"""
Rich terminal display helpers.
Color-coded panels and progress indicators for each agent.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from contextlib import contextmanager

console = Console(legacy_windows=False)

# Agent color scheme
AGENT_STYLES = {
    "supervisor":        {"color": "yellow",        "emoji": "🎯", "title": "Supervisor"},
    "product_manager":   {"color": "dodger_blue1",  "emoji": "📋", "title": "Product Manager"},
    "architect":         {"color": "medium_purple3", "emoji": "🏗️", "title": "Architect"},
    "tech_strategist":   {"color": "dark_orange3",   "emoji": "⚙️", "title": "Tech Strategist"},
    "critic":            {"color": "red1",           "emoji": "🔍", "title": "Design Critic"},
    "prototype_builder": {"color": "green3",         "emoji": "🛠️", "title": "Prototype Builder"},
    "qa_validator":      {"color": "cyan1",          "emoji": "✅", "title": "QA Validator"},
    "error_resolver":      {"color": "magenta",        "emoji": "🎯", "title": "Goal Tracker"},
    "delivery_agent":    {"color": "bright_green",   "emoji": "📦", "title": "Delivery Agent"},
    "qa_lead":           {"color": "spring_green3",  "emoji": "🔬", "title": "QA Lead"},
}


def show_banner():
    """Display the application banner."""
    banner = Text()
    banner.append("╔══════════════════════════════════════════════╗\n", style="bold bright_cyan")
    banner.append("║     ", style="bold bright_cyan")
    banner.append("AI Solution Architect", style="bold bright_white")
    banner.append("                   ║\n", style="bold bright_cyan")
    banner.append("║     ", style="bold bright_cyan")
    banner.append("Multi-Agent Design System", style="dim bright_cyan")
    banner.append("              ║\n", style="bold bright_cyan")
    banner.append("║                                              ║\n", style="bold bright_cyan")
    banner.append("║     ", style="bold bright_cyan")
    banner.append("Powered by LangGraph + NVIDIA NIM", style="dim")
    banner.append("       ║\n", style="bold bright_cyan")
    banner.append("╚══════════════════════════════════════════════╝", style="bold bright_cyan")
    console.print(banner)
    console.print()


def show_agent_output(agent_name: str, content: str):
    """Display an agent's output in a color-coded panel."""
    style = AGENT_STYLES.get(agent_name, {"color": "white", "emoji": "🤖", "title": agent_name})

    panel = Panel(
        content,
        title=f"{style['emoji']} {style['title']}",
        border_style=style["color"],
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def show_phase(phase_name: str):
    """Display a phase transition header."""
    console.print()
    console.rule(f"[bold bright_cyan]Phase: {phase_name}[/]")
    console.print()


@contextmanager
def show_thinking(agent_name: str):
    """Show a spinner while an agent is thinking."""
    style = AGENT_STYLES.get(agent_name, {"emoji": "🤖", "title": agent_name})
    with Progress(
        SpinnerColumn(style="bright_cyan"),
        TextColumn(f"[bold]{style['emoji']} {style['title']}[/] is thinking..."),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("", total=None)
        yield


def show_routing(from_agent: str, to_agent: str):
    """Display a routing decision."""
    from_style = AGENT_STYLES.get(from_agent, {"emoji": "🤖", "title": from_agent})
    to_style = AGENT_STYLES.get(to_agent, {"emoji": "🤖", "title": to_agent})

    console.print(
        f"  [dim]→ Routing:[/] {from_style['emoji']} {from_style['title']} "
        f"[dim]──▶[/] {to_style['emoji']} {to_style['title']}",
    )
    console.print()


def show_critique_result(approved: bool, issues: list[str], suggestions: list[str]):
    """Display critique results with clear approved/rejected status."""
    if approved:
        console.print("[bold green]✅ DESIGN APPROVED[/]")
    else:
        console.print("[bold red]❌ DESIGN REJECTED — Revisions Required[/]")

    from rich.markup import escape
    if issues:
        console.print("\n[bold red]Issues:[/]")
        for issue in issues:
            console.print(f"  [red]•[/] {escape(issue)}")

    if suggestions:
        console.print("\n[bold yellow]Suggestions:[/]")
        for suggestion in suggestions:
            console.print(f"  [yellow]•[/] {escape(suggestion)}")
    console.print()


def show_file_tree(files: list[dict]):
    """Display the generated project file tree."""
    tree = Tree("📁 [bold]Generated Project[/]")

    # Group files by directory
    dirs = {}
    for f in files:
        parts = f["path"].replace("\\", "/").split("/")
        current = dirs
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = None

    def add_to_tree(node, d):
        for name, children in sorted(d.items()):
            if children is None:
                node.add(f"📄 {name}")
            else:
                branch = node.add(f"📁 [bold]{name}[/]")
                add_to_tree(branch, children)

    add_to_tree(tree, dirs)
    console.print(tree)
    console.print()


def show_qa_results(requirement_checks: list[dict], approved: bool):
    """Display QA validation results as a table."""
    table = Table(title="📊 Requirements Coverage Report")
    table.add_column("Requirement", style="white", max_width=40)
    table.add_column("Status", justify="center", width=8)
    table.add_column("Evidence", style="dim", max_width=40)

    from rich.markup import escape
    for check in requirement_checks:
        status = "[green]✅ PASS[/]" if check.get("covered") else "[red]❌ FAIL[/]"
        table.add_row(
            escape(check.get("requirement", "")),
            status,
            escape(check.get("evidence", "")),
        )

    console.print(table)
    console.print()

    if approved:
        console.print("[bold green]✅ QA VALIDATION PASSED[/]\n")
    else:
        console.print("[bold red]❌ QA VALIDATION FAILED — Prototype needs revision[/]\n")


def ask_approval(prompt: str = "Approve and continue?") -> bool:
    """Ask the user for approval (human-in-the-loop)."""
    console.print(f"\n[bold yellow]⏸️  {prompt}[/]")
    response = console.input("[dim](y/n): [/]").strip().lower()
    return response in ("y", "yes", "")


def show_complete(output_dir: str):
    """Display completion message."""
    console.print()
    panel = Panel(
        f"[bold green]All agents have completed their work![/]\n\n"
        f"📁 Output saved to: [bold cyan]{output_dir}[/]\n\n"
        f"[dim]cd into the project folder and follow the README to get started.[/]",
        title="🎉 Done!",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()
