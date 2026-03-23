"""
Prismo CLI — command-line interface for recording and replaying AI agent sessions.

Commands:
    prismo record <name> -- <command>    Record an agent session
    prismo sessions                       List recorded sessions
    prismo replay <session_id>           Replay a session in the terminal
    prismo upload <session_id>           Upload a session to the dashboard
    prismo serve                          Start the Prismo server + dashboard
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

app = typer.Typer(
    name="prismo",
    help="Deterministic replay & counterfactual debugging for AI agents",
    add_completion=False,
)
console = Console()

# Default data directory
DATA_DIR = Path.home() / ".prismo" / "sessions"


def _get_data_dir() -> Path:
    """Get the Prismo data directory, creating it if needed."""
    data_dir = Path(os.environ.get("PRISMO_DATA_DIR", str(DATA_DIR)))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _session_path(session_id: str) -> Path:
    """Get the file path for a session."""
    return _get_data_dir() / f"{session_id}.json"


def _save_session(session: "Session") -> Path:
    """Save a session to disk."""
    from .utils.serialization import serialize
    path = _session_path(session.session_id)
    path.write_text(serialize(session.model_dump()))
    return path


def _load_session(session_id: str) -> "Session":
    """Load a session from disk."""
    from .models import Session
    path = _session_path(session_id)
    if not path.exists():
        # Try partial match
        matches = list(_get_data_dir().glob(f"{session_id}*.json"))
        if not matches:
            raise typer.BadParameter(f"Session {session_id!r} not found")
        path = matches[0]
    data = json.loads(path.read_text())
    return Session.model_validate(data)


def _list_sessions() -> list[dict]:
    """List all sessions from disk."""
    sessions = []
    for path in sorted(_get_data_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text())
            sessions.append(data)
        except Exception:
            continue
    return sessions


@app.command()
def record(
    name: str = typer.Argument(..., help="Name for this recording session"),
    command: list[str] = typer.Argument(..., help="Command to run (after --)"),
    watch: Optional[str] = typer.Option(None, "--watch", "-w", help="Directory to watch for file changes"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path for session JSON"),
) -> None:
    """
    Record an AI agent session.

    Example:
        prismo record "Fix auth bug" -- python my_agent.py
    """
    from .recorder import PrismoRecorder
    from .interceptors.anthropic import AnthropicInterceptor
    from .interceptors.openai import OpenAIInterceptor

    if not command:
        console.print("[red]Error:[/red] No command specified. Use: prismo record <name> -- <command>")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold blue]PRISMO[/bold blue] — Recording session\n"
        f"Name: [bold]{name}[/bold]\n"
        f"Command: [cyan]{' '.join(command)}[/cyan]",
        border_style="blue",
    ))

    recorder = PrismoRecorder()
    session_id = recorder.start_session(name, metadata={"command": " ".join(command)})
    console.print(f"[dim]Session ID: {session_id}[/dim]")

    # Install interceptors
    anthropic_interceptor = AnthropicInterceptor(recorder)
    openai_interceptor = OpenAIInterceptor(recorder)
    anthropic_interceptor.install()
    openai_interceptor.install()

    # Start file watcher if requested
    watcher = None
    if watch:
        try:
            from .watchers.filesystem import FileSystemWatcher
            watcher = FileSystemWatcher(watch, recorder)
            watcher.start()
            console.print(f"[dim]Watching {watch} for file changes[/dim]")
        except ImportError:
            console.print("[yellow]Warning:[/yellow] watchdog not installed; file watching disabled")

    exit_code = 0
    try:
        # Run the command
        result = subprocess.run(command, capture_output=False)
        exit_code = result.returncode
    except KeyboardInterrupt:
        console.print("\n[yellow]Recording interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Command failed:[/red] {e}")
        exit_code = 1
    finally:
        # Clean up
        anthropic_interceptor.uninstall()
        openai_interceptor.uninstall()
        if watcher:
            watcher.stop()

    # End the session
    if exit_code != 0:
        session = recorder.fail_session(f"Command exited with code {exit_code}")
    else:
        session = recorder.end_session()

    # Save to disk
    save_path = _session_path(session_id)
    if output:
        save_path = Path(output)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    from .utils.serialization import serialize
    save_path.write_text(serialize(session.model_dump()))

    console.print(Panel(
        f"[bold green]Session recorded![/bold green]\n"
        f"ID: [cyan]{session_id}[/cyan]\n"
        f"Events: [bold]{len(session.events)}[/bold] "
        f"({session.summary.total_llm_calls} LLM calls, "
        f"{session.summary.files_modified + session.summary.files_created} file changes)\n"
        f"Saved: [dim]{save_path}[/dim]",
        border_style="green",
    ))


@app.command()
def sessions() -> None:
    """List all recorded sessions."""
    session_list = _list_sessions()

    if not session_list:
        console.print("[dim]No sessions recorded yet. Use [bold]prismo record[/bold] to start.[/dim]")
        return

    table = Table(title="Recorded Sessions", border_style="blue")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Date", style="dim")
    table.add_column("LLM Calls", justify="right")
    table.add_column("Files Changed", justify="right")
    table.add_column("Events", justify="right")

    status_colors = {
        "completed": "[green]●[/green]",
        "failed": "[red]●[/red]",
        "recording": "[yellow]●[/yellow]",
    }

    for s in session_list:
        status = s.get("status", "unknown")
        summary = s.get("summary", {})
        started = s.get("started_at", "")[:19].replace("T", " ")

        files_changed = (
            summary.get("files_created", 0) +
            summary.get("files_modified", 0) +
            summary.get("files_deleted", 0)
        )

        table.add_row(
            s.get("session_id", "")[:12] + "...",
            s.get("name", "Unnamed"),
            status_colors.get(status, status),
            started,
            str(summary.get("total_llm_calls", 0)),
            str(files_changed),
            str(len(s.get("events", []))),
        )

    console.print(table)


@app.command()
def replay(
    session_id: str = typer.Argument(..., help="Session ID to replay"),
    speed: float = typer.Option(1.0, "--speed", "-s", help="Playback speed (1.0 = real-time)"),
) -> None:
    """Replay a recorded session in the terminal."""
    from .models import LLMCallEvent, ToolCallEvent, FileChangeEvent, TerminalCommandEvent
    from .replay import PrismoReplayer

    try:
        session = _load_session(session_id)
    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold blue]PRISMO REPLAY[/bold blue]\n"
        f"Session: [bold]{session.name}[/bold]\n"
        f"Events: {len(session.events)} | Speed: {speed}x",
        border_style="blue",
    ))

    replayer = PrismoReplayer(session)
    event_colors = {
        "llm_call": "blue",
        "tool_call": "magenta",
        "file_change": "green",
        "terminal_cmd": "yellow",
    }

    for event in replayer.replay(speed=speed):
        color = event_colors.get(event.event_type.value, "white")
        icon = {
            "llm_call": "🧠",
            "tool_call": "🔧",
            "file_change": "📄",
            "terminal_cmd": "💻",
        }.get(event.event_type.value, "•")

        console.print(
            f"[dim]{event.timestamp.strftime('%H:%M:%S.%f')[:-3]}[/dim] "
            f"[{color}]{icon} {event.description}[/{color}]"
        )

        # Show details for LLM calls
        if isinstance(event, LLMCallEvent):
            console.print(
                f"  [dim]→ {event.token_usage.total_tokens} tokens | "
                f"{event.latency_ms:.0f}ms | "
                f"stop: {event.stop_reason}[/dim]"
            )
        elif isinstance(event, TerminalCommandEvent):
            if event.had_error:
                console.print(f"  [red]→ exit code: {event.exit_code}[/red]")

    console.print(f"\n[bold green]Replay complete[/bold green] — {len(session.events)} events")


@app.command()
def upload(
    session_id: str = typer.Argument(..., help="Session ID to upload"),
    server: str = typer.Option("http://localhost:8000", "--server", help="Prismo server URL"),
) -> None:
    """Upload a session to the Prismo dashboard server."""
    import httpx

    try:
        session = _load_session(session_id)
    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(f"Uploading session [cyan]{session_id}[/cyan] to [dim]{server}[/dim]...")

    try:
        from .utils.serialization import serialize
        response = httpx.post(
            f"{server}/api/sessions",
            content=serialize(session.model_dump()),
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )
        response.raise_for_status()
        result = response.json()
        console.print(
            f"[bold green]Uploaded![/bold green] "
            f"View at: [link]{server}/session/{result.get('session_id', session_id)}[/link]"
        )
    except Exception as e:
        console.print(f"[red]Upload failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload"),
) -> None:
    """Start the Prismo server and dashboard."""
    import uvicorn

    console.print(Panel(
        f"[bold blue]PRISMO SERVER[/bold blue]\n"
        f"Dashboard: [link]http://{host}:{port}[/link]\n"
        f"API docs: [link]http://{host}:{port}/docs[/link]",
        border_style="blue",
    ))

    # Try to find the server module
    try:
        uvicorn.run(
            "server.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except ModuleNotFoundError:
        console.print(
            "[red]Error:[/red] Prismo server not found. "
            "Make sure you're running from the project root."
        )
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the Prismo CLI."""
    app()


if __name__ == "__main__":
    main()
