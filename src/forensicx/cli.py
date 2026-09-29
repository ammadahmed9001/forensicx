"""ForensicX command-line interface."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from forensicx.core import database as db
from forensicx.core.models import Case
from forensicx.services.evidence import import_evidence
from forensicx.services.reports import export_case_json

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """ForensicX — Android digital forensics platform."""


# ── case ──────────────────────────────────────────────────────────────────────

@main.group()
def case() -> None:
    """Manage cases."""


@case.command("create")
@click.argument("name")
@click.option("--investigator", "-i", default="Unknown", show_default=True)
@click.option("--notes", default="")
def case_create(name: str, investigator: str, notes: str) -> None:
    """Create a new case."""
    c = db.create_case(name=name, investigator=investigator, notes=notes)
    console.print(f"[green]Created case #{c.id}:[/] {c.name}")


@case.command("list")
def case_list() -> None:
    """List all cases."""
    cases = db.list_cases()
    if not cases:
        console.print("[yellow]No cases found.[/]")
        return
    t = Table(title="Cases")
    t.add_column("ID", style="cyan")
    t.add_column("Name")
    t.add_column("Investigator")
    t.add_column("Created")
    for c in cases:
        t.add_row(str(c.id), c.name, c.investigator, c.created_at.strftime("%Y-%m-%d %H:%M"))
    console.print(t)


# ── evidence ──────────────────────────────────────────────────────────────────

@main.group()
def evidence() -> None:
    """Manage evidence items."""


@evidence.command("import")
@click.argument("case_id", type=int)
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--parser", default="generic_text", show_default=True)
@click.option("--notes", default="")
def evidence_import(case_id: int, file_path: str, parser: str, notes: str) -> None:
    """Import and parse an evidence file into a case."""
    ev = import_evidence(case_id=case_id, file_path=file_path, parser_name=parser, notes=notes)
    console.print(
        f"[green]Imported evidence #{ev.id}:[/] {ev.filename}  "
        f"sha256={ev.sha256[:16]}…"
    )


@evidence.command("list")
@click.argument("case_id", type=int)
def evidence_list(case_id: int) -> None:
    """List evidence items in a case."""
    items = db.list_evidence(case_id)
    if not items:
        console.print("[yellow]No evidence for this case.[/]")
        return
    t = Table(title=f"Evidence — case #{case_id}")
    t.add_column("ID", style="cyan")
    t.add_column("Filename")
    t.add_column("Parser")
    t.add_column("SHA-256 (prefix)")
    t.add_column("Size")
    for e in items:
        t.add_row(
            str(e.id),
            e.filename,
            e.parser,
            e.sha256[:16] + "…",
            f"{e.size_bytes:,} B",
        )
    console.print(t)


# ── search ────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("case_id", type=int)
@click.argument("query")
@click.option("--limit", default=50, show_default=True)
def search(case_id: int, query: str, limit: int) -> None:
    """Full-text search across all artifacts in a case."""
    results = db.search_artifacts(case_id, query, limit=limit)
    if not results:
        console.print("[yellow]No results.[/]")
        return
    t = Table(title=f"Search: {query!r} in case #{case_id}")
    t.add_column("ID", style="cyan")
    t.add_column("Type")
    t.add_column("Source")
    t.add_column("Content")
    for r in results:
        t.add_row(str(r.id), r.artifact_type, r.source, r.content[:120])
    console.print(t)


# ── report ────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("case_id", type=int)
@click.argument("output_path", type=click.Path())
def report(case_id: int, output_path: str) -> None:
    """Export a case report as JSON."""
    out = export_case_json(case_id, output_path)
    console.print(f"[green]Report written:[/] {out}")


# ── gui ───────────────────────────────────────────────────────────────────────

@main.command()
def gui() -> None:
    """Launch the ForensicX case management GUI."""
    try:
        from forensicx.gui.app import run_gui
        run_gui()
    except ImportError as exc:
        console.print(f"[red]GUI dependencies not available:[/] {exc}")
        sys.exit(1)


@main.command()
def hub() -> None:
    """Launch the ForensicX multi-tool hub (Tkinter desktop app)."""
    try:
        from forensicx_hub.app import run_hub
        run_hub()
    except ImportError as exc:
        console.print(f"[red]Hub dependencies not available:[/] {exc}")
        sys.exit(1)


@main.command()
@click.option("--port", default=5000, show_default=True, help="HTTP port to listen on.")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically.")
def web(port: int, host: str, no_browser: bool) -> None:
    """Launch the ForensicX professional web dashboard (recommended)."""
    try:
        from forensicx_hub.web_app import run_web
        run_web(host=host, port=port, open_browser=not no_browser)
    except ImportError as exc:
        console.print(f"[red]Flask not available:[/] {exc}")
        console.print("Install with: [bold]pip install flask flask-socketio[/]")
        sys.exit(1)
