"""
AI Solution Architect — Multi-Agent Design System
CLI entry point.

Usage:
  python main.py                          # Interactive (human-in-the-loop)
  python main.py --auto                   # Fully autonomous
  python main.py --fix output/MyProject   # Fix/validate an existing project
"""

import argparse
import os
import uuid
import sys

# Force UTF-8 on Windows where the default codec (cp1252) can't encode Rich's
# box-drawing characters. Must happen before any Rich imports.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import OUTPUT_DIR
from graph.workflow import compile_graph
from utils.loop_controller import make_goal
from utils.display import (
    console,
    show_banner,
    show_complete,
    show_agent_output,
)
from utils import logger as log
from utils.logger import setup_logger
from utils.session import load_existing_project


def get_requirements() -> str:
    """Prompt the user for requirements (multi-line input)."""
    console.print(
        "[bold bright_cyan]Describe what you want to build.[/]\n"
        "[dim]Type your requirements below. Press Enter twice (empty line) to submit.[/]\n"
    )

    lines = []
    while True:
        try:
            line = input()
            if line == "" and lines and lines[-1] == "":
                break
            lines.append(line)
        except EOFError:
            break

    requirements = "\n".join(lines).strip()

    if not requirements:
        console.print("[red]No requirements provided. Exiting.[/]")
        sys.exit(1)

    return requirements


def resolve_fix_path(raw_path: str) -> str:
    """
    Resolve a --fix argument to an absolute folder path.
    Accepts:
      - Absolute path:            D:\\...\\output\\MyProject
      - Relative path:            output/MyProject
      - Just the folder name:     MyProject  (looked up inside OUTPUT_DIR)
    """
    # Already absolute
    if os.path.isabs(raw_path):
        return raw_path

    # Relative path from CWD
    if os.path.isdir(raw_path):
        return os.path.abspath(raw_path)

    # Just a project name — look inside OUTPUT_DIR
    candidate = os.path.join(OUTPUT_DIR, raw_path)
    if os.path.isdir(candidate):
        return candidate

    # Can't resolve
    return os.path.abspath(raw_path)  # Will fail later with a clear error


def run(auto_mode: bool = False, fix_path: str = None):
    """Run the multi-agent design workflow."""
    show_banner()

    # Initialize logger
    logger_instance, log_file = setup_logger()
    log.init(logger_instance)
    console.print(f"[dim]📄 Logging to: {log_file}[/]\n")

    # ─────────────────────────────
    # FIX MODE: load existing project
    # ─────────────────────────────
    if fix_path:
        resolved = resolve_fix_path(fix_path)
        console.print(
            f"[bold yellow]🔧 Fix Mode[/] — Loading existing project from:\n"
            f"  [dim]{resolved}[/]\n"
        )

        try:
            initial_state = load_existing_project(resolved)
        except FileNotFoundError as e:
            console.print(f"[bold red]❌ {e}[/]")
            sys.exit(1)
        except ValueError as e:
            console.print(f"[bold red]❌ Session error: {e}[/]")
            sys.exit(1)

        # Override auto_mode in fix mode — always autonomous
        initial_state["auto_mode"] = True

        project_name = (initial_state.get("product_spec") or {}).get("project_name", os.path.basename(resolved))
        reqs_preview = initial_state.get("requirements", "")[:80]
        log.requirements_received(initial_state.get("requirements", ""))

        show_agent_output(
            "supervisor",
            f"[bold]Fix Mode — Resuming project:[/] {project_name}\n\n"
            f"[dim]Requirements: {reqs_preview}...[/]\n"
            f"[dim]Files loaded: {len(initial_state['prototype'].get('files', []))}[/]\n\n"
            f"[dim]Running QA validation → auto-fix loop...[/]"
        )

    # ─────────────────────────────
    # NORMAL MODE: start from scratch
    # ─────────────────────────────
    else:
        requirements = get_requirements()
        log.requirements_received(requirements)

        console.print()
        show_agent_output(
            "supervisor",
            f"[bold]Requirements received![/]\n\n{requirements}\n\n"
            f"[dim]Starting multi-agent design pipeline...\n"
            f"Mode: {'🤖 Autonomous' if auto_mode else '👤 Human-in-the-Loop'}[/]"
        )

        # Seed the goal stack with the root goal — everything the system does
        # is in service of proving this goal to QA.
        main_goal = make_goal(
            goal_type="main_build",
            description=f"Build: {requirements[:120]}",
            resume_agent="done",
        )

        initial_state = {
            "messages": [],
            "requirements": requirements,
            "product_spec": None,
            "architecture": None,
            "tech_stack": None,
            "critique": None,
            "prototype": None,
            "qa_result": None,
            "resolution_queue": [main_goal],
            "revision_count": 0,
            "debug_iteration": 0,
            "total_patch_count": 0,
            "sandbox_attempts": 0,
            "test_engineer_attempts": 0,
            "planning_done": False,
            "oversized_files": None,
            "current_phase": "Starting",
            "next_agent": "",
            "auto_mode": auto_mode,
            "fix_mode": False,
        }

    # Compile and run the graph
    app = compile_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    from tools.session import cleanup_all_sessions
    
    try:
        final_state = app.invoke(initial_state, config=config)

        prototype = final_state.get("prototype", {})
        output_dir = prototype.get("output_dir", OUTPUT_DIR)
        project_name = (final_state.get("product_spec") or {}).get("project_name", "unknown")
        
        current_phase = final_state.get("current_phase", "")
        if "🛑" in current_phase or "❌" in current_phase:
            console.print()
            from rich.panel import Panel
            panel = Panel(
                f"[bold red]Workflow Aborted[/]\n\n"
                f"The system escalated or stopped at phase: [bold]{current_phase}[/]\n"
                f"📁 Partial output saved to: [cyan]{output_dir}[/]\n\n"
                f"[dim]You can manually fix the issue in the output directory, then run:[/]\n"
                f"[dim bright_white]python main.py --fix {output_dir}[/]",
                title="🛑 Escalation / Failure",
                border_style="red",
                padding=(1, 2),
            )
            console.print(panel)
            log.run_complete(project_name, output_dir)
        else:
            log.run_complete(project_name, output_dir)
            show_complete(output_dir)

    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️  Pipeline interrupted by user.[/]")
        log.run_error(KeyboardInterrupt("Interrupted by user"))
        sys.exit(0)
    except RuntimeError as e:
        error_msg = str(e)
        if "rate-limited" in error_msg or "unavailable" in error_msg:
            from rich.panel import Panel
            console.print()
            console.print(Panel(
                f"[bold yellow]All LLM providers are currently rate-limited or unavailable.[/]\n\n"
                f"Please wait a while and try again.\n\n"
                f"[dim]No output was saved — the run did not complete.[/]",
                title="⏸️  Rate Limit — Run Stopped",
                border_style="yellow",
                padding=(1, 2),
            ))
            log.run_error(e)
            sys.exit(1)
        else:
            console.print(f"\n[bold red]❌ Error:[/] {e}")
            log.run_error(e)
            raise
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/] {e}")
        console.print("[dim]Check your API key and network connection.[/]")
        log.run_error(e)
        raise
    finally:
        cleanup_all_sessions()


def main():
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="AI Solution Architect — Multi-Agent Design System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py                            # Interactive (human-in-the-loop)\n"
            "  python main.py --auto                     # Fully autonomous\n"
            "  python main.py --fix output/Rust_Todo_App # Fix an existing project\n"
            "  python main.py --fix Rust_Todo_App        # Same (auto-resolves from output/)\n"
        ),
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run in autonomous mode (no human approval pauses)",
    )
    parser.add_argument(
        "--fix",
        metavar="PATH",
        help=(
            "Fix/validate an existing project. Pass the path to the project folder "
            "(e.g. 'output/Rust_Todo_App' or just 'Rust_Todo_App'). "
            "Skips design phases and runs QA + auto-fix on existing code."
        ),
    )
    args = parser.parse_args()

    if args.fix and args.auto:
        console.print("[yellow]Note: --fix always runs in autonomous mode. --auto flag is redundant.[/]")

    run(auto_mode=args.auto, fix_path=args.fix)


if __name__ == "__main__":
    main()
