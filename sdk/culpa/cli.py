"""
Culpa CLI — command-line interface for recording and replaying AI agent sessions.

Commands:
    culpa record <name> -- <command>    Record an agent session
    culpa sessions                       List recorded sessions
    culpa replay <session_id>           Replay a session in the terminal
    culpa upload <session_id>           Upload a session to the dashboard
    culpa serve                          Start the Culpa server + dashboard
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(
    name="culpa",
    help="Deterministic replay & counterfactual debugging for AI agents",
    add_completion=False,
)
console = Console()

DATA_DIR = Path.home() / ".culpa" / "sessions"
CONFIG_PATH = Path.home() / ".culpa" / "config.json"


def _load_config() -> dict:
    """Load ~/.culpa/config.json, return empty dict if missing."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_config(config: dict) -> None:
    """Persist config to ~/.culpa/config.json."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def _get_api_key() -> Optional[str]:
    """Return API key from env var, then config file."""
    return os.environ.get("CULPA_API_KEY") or _load_config().get("api_key")


def _get_server_url() -> str:
    """Return server URL from env var, then config file, then default."""
    return (
        os.environ.get("CULPA_SERVER_URL")
        or _load_config().get("server_url")
        or "http://localhost:8000"
    )


def _try_upload(session_json: str, session_id: str) -> bool:
    """Attempt to upload a session if an API key is configured. Returns True on success."""
    key = _get_api_key()
    if not key:
        return False

    server = _get_server_url()
    try:
        import httpx
        response = httpx.post(
            f"{server}/api/sessions",
            content=session_json,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        console.print(f"[green]Uploaded to {server}[/green]")
        return True
    except Exception as e:
        console.print(f"[dim]Auto-upload failed ({e}). Session saved locally.[/dim]")
        return False


def _get_data_dir() -> Path:
    """Get the Culpa data directory, creating it if needed."""
    data_dir = Path(os.environ.get("CULPA_DATA_DIR", str(DATA_DIR)))
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
def login(
    server: str = typer.Option("http://localhost:8000", "--server", help="Culpa server URL"),
) -> None:
    """Authenticate with a Culpa server and save credentials locally."""
    import httpx

    console.print(f"[bold]Logging in to[/bold] [cyan]{server}[/cyan]\n")
    email = typer.prompt("Email")
    password = typer.prompt("Password", hide_input=True)

    try:
        client = httpx.Client(base_url=server, timeout=15.0)
        resp = client.post("/api/auth/login", json={"email": email, "password": password})
        if resp.status_code == 401:
            console.print("[red]Invalid email or password.[/red]")
            raise typer.Exit(1)
        resp.raise_for_status()

        key_resp = client.post(
            "/api/keys",
            json={"name": "CLI"},
            cookies=resp.cookies,
        )
        key_resp.raise_for_status()
        api_key = key_resp.json()["key"]

        config = _load_config()
        config["api_key"] = api_key
        config["server_url"] = server
        _save_config(config)

        console.print(f"[bold green]Logged in![/bold green] Credentials saved to [dim]{CONFIG_PATH}[/dim]")
        console.print(f"API key: [cyan]{api_key[:16]}...[/cyan]")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Login failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def record(
    name: str = typer.Argument(..., help="Name for this recording session"),
    command: list[str] = typer.Argument(..., help="Command to run (after --)"),
    watch: Optional[str] = typer.Option(None, "--watch", "-w", help="Directory to watch for file changes"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path for session JSON"),
) -> None:
    """
    Record an AI agent session.

    The child process must call culpa.init() and culpa.stop() — the CLI
    communicates with it via the CULPA_RECORD_OUTPUT env var so the session
    is handed back to this process after the child exits.

    Example:
        culpa record "Fix auth bug" -- python my_agent.py
    """
    import tempfile

    if not command:
        console.print("[red]Error:[/red] No command specified. Use: culpa record <name> -- <command>")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold blue]CULPA[/bold blue] — Recording session\n"
        f"Name: [bold]{name}[/bold]\n"
        f"Command: [cyan]{' '.join(command)}[/cyan]",
        border_style="blue",
    ))

    handoff_dir = Path.home() / ".culpa" / "handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    handoff_path = handoff_dir / f"record_{os.getpid()}.json"

    env = os.environ.copy()
    env["CULPA_RECORD_OUTPUT"] = str(handoff_path)
    env["CULPA_SESSION_NAME"] = name
    env["CULPA_NO_AUTO_UPLOAD"] = "1"

    console.print(f"[dim]Handoff file: {handoff_path}[/dim]")

    exit_code = 0
    try:
        result = subprocess.run(command, capture_output=False, env=env)
        exit_code = result.returncode
    except KeyboardInterrupt:
        console.print("\n[yellow]Recording interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Command failed:[/red] {e}")
        exit_code = 1

    if not handoff_path.exists():
        console.print(
            "[red]No session data received from child process.[/red]\n"
            "Make sure your script calls [bold]culpa.init()[/bold] and [bold]culpa.stop()[/bold]."
        )
        raise typer.Exit(1)

    try:
        from .models import Session
        session_data = json.loads(handoff_path.read_text())
        session = Session.model_validate(session_data)
    except Exception as e:
        console.print(f"[red]Failed to read session from child process:[/red] {e}")
        raise typer.Exit(1)
    finally:
        handoff_path.unlink(missing_ok=True)

    session_id = session.session_id
    save_path = _session_path(session_id)
    if output:
        save_path = Path(output)

    save_path.parent.mkdir(parents=True, exist_ok=True)
    from .utils.serialization import serialize
    session_json = serialize(session.model_dump())
    save_path.write_text(session_json)

    console.print(Panel(
        f"[bold green]Session recorded![/bold green]\n"
        f"ID: [cyan]{session_id}[/cyan]\n"
        f"Events: [bold]{len(session.events)}[/bold] "
        f"({session.summary.total_llm_calls} LLM calls, "
        f"{session.summary.files_modified + session.summary.files_created} file changes)\n"
        f"Saved: [dim]{save_path}[/dim]",
        border_style="green",
    ))

    _try_upload(session_json, session_id)


@app.command()
def sessions() -> None:
    """List all recorded sessions."""
    session_list = _list_sessions()

    if not session_list:
        console.print("[dim]No sessions recorded yet. Use [bold]culpa record[/bold] to start.[/dim]")
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

        raw_ts = s.get("started_at", "")
        try:
            from datetime import datetime, timezone as tz
            dt = datetime.fromisoformat(raw_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz.utc)
            local_dt = dt.astimezone()
            started = local_dt.strftime("%b %d, %Y %-I:%M %p")
        except Exception:
            started = raw_ts[:19].replace("T", " ")

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
    from .replay import CulpaReplayer

    try:
        session = _load_session(session_id)
    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold blue]CULPA REPLAY[/bold blue]\n"
        f"Session: [bold]{session.name}[/bold]\n"
        f"Events: {len(session.events)} | Speed: {speed}x",
        border_style="blue",
    ))

    replayer = CulpaReplayer(session)
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
    server: Optional[str] = typer.Option(None, "--server", help="Culpa server URL"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="API key (overrides config/env)"),
) -> None:
    """Upload a session to the Culpa dashboard server."""
    import httpx

    try:
        session = _load_session(session_id)
    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    target_server = server or _get_server_url()
    key = api_key or _get_api_key()

    if not key:
        console.print(
            "[red]No API key found.[/red] Run [bold]culpa login[/bold] or "
            "set [cyan]CULPA_API_KEY[/cyan] environment variable."
        )
        raise typer.Exit(1)

    console.print(f"Uploading session [cyan]{session_id}[/cyan] to [dim]{target_server}[/dim]...")

    try:
        from .utils.serialization import serialize
        response = httpx.post(
            f"{target_server}/api/sessions",
            content=serialize(session.model_dump()),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        result = response.json()
        console.print(
            f"[bold green]Uploaded![/bold green] "
            f"View at: [link]{target_server}/session/{result.get('session_id', session_id)}[/link]"
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
    """Start the Culpa server and dashboard."""
    import uvicorn

    console.print(Panel(
        f"[bold blue]CULPA SERVER[/bold blue]\n"
        f"Dashboard: [link]http://{host}:{port}[/link]\n"
        f"API docs: [link]http://{host}:{port}/docs[/link]",
        border_style="blue",
    ))

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
            "[red]Error:[/red] Culpa server not found. "
            "Make sure you're running from the project root."
        )
        raise typer.Exit(1)


proxy_app = typer.Typer(name="proxy", help="Transparent LLM proxy for recording Claude Code, Cursor, etc.")
app.add_typer(proxy_app)


@proxy_app.command("start")
def proxy_start(
    port: int = typer.Option(4560, "--port", "-p", help="Port to listen on"),
    name: str = typer.Option("culpa-proxy", "--name", "-n", help="Session name"),
    watch: Optional[str] = typer.Option(None, "--watch", "-w", help="Directory to watch for file changes"),
    background: bool = typer.Option(False, "--background", "-b", help="Run in the background"),
) -> None:
    """Start the Culpa proxy server for recording LLM calls."""
    from .proxy import PID_FILE, run_proxy

    if PID_FILE.exists():
        try:
            info = json.loads(PID_FILE.read_text())
            pid = info["pid"]
            os.kill(pid, 0)
            console.print(
                f"[yellow]Proxy already running[/yellow] (PID {pid}, port {info['port']})\n"
                f"Stop it first: [bold]culpa proxy stop[/bold]"
            )
            raise typer.Exit(1)
        except (ProcessLookupError, OSError):
            PID_FILE.unlink(missing_ok=True)

    if background:
        pid = os.fork()
        if pid > 0:
            import time
            time.sleep(1)
            if PID_FILE.exists():
                info = json.loads(PID_FILE.read_text())
                console.print(Panel(
                    f"[bold green]Culpa proxy started in background[/bold green]\n"
                    f"PID: {info['pid']}\n"
                    f"Port: {info['port']}\n"
                    f"Session: [cyan]{info['session_id']}[/cyan]\n"
                    f"\nPoint your AI tool at:\n"
                    f"  [bold]ANTHROPIC_BASE_URL=http://localhost:{port}[/bold]",
                    border_style="green",
                ))
            else:
                console.print("[red]Failed to start proxy in background[/red]")
                raise typer.Exit(1)
            return
        else:
            os.setsid()
            import sys
            sys.stdin.close()
            log_path = Path.home() / ".culpa" / "proxy.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_fd = open(log_path, "a")
            os.dup2(log_fd.fileno(), 1)
            os.dup2(log_fd.fileno(), 2)
    else:
        console.print(Panel(
            f"[bold blue]CULPA PROXY[/bold blue]\n"
            f"Listening on: [bold]http://localhost:{port}[/bold]\n"
            f"Session: [bold]{name}[/bold]\n"
            f"\nPoint your AI tool at:\n"
            f"  [bold]ANTHROPIC_BASE_URL=http://localhost:{port}[/bold]\n"
            f"  [bold]OPENAI_BASE_URL=http://localhost:{port}[/bold]\n"
            f"\nPress Ctrl+C to stop and save the session.",
            border_style="blue",
        ))

    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    run_proxy(port=port, session_name=name, watch_dir=watch)


@proxy_app.command("stop")
def proxy_stop() -> None:
    """Stop the running Culpa proxy and save the session."""
    from .proxy import PID_FILE

    if not PID_FILE.exists():
        console.print("[dim]No proxy is currently running.[/dim]")
        raise typer.Exit(1)

    try:
        info = json.loads(PID_FILE.read_text())
        pid = info["pid"]
        os.kill(pid, signal.SIGTERM)
        console.print(f"[green]Proxy stopped[/green] (PID {pid})")
        console.print(f"Session: [cyan]{info.get('session_id', '?')}[/cyan]")
    except ProcessLookupError:
        console.print("[yellow]Proxy process not found — cleaning up PID file.[/yellow]")
        PID_FILE.unlink(missing_ok=True)
    except Exception as e:
        console.print(f"[red]Failed to stop proxy:[/red] {e}")
        raise typer.Exit(1)


@proxy_app.command("status")
def proxy_status() -> None:
    """Check if the Culpa proxy is running."""
    from .proxy import PID_FILE

    if not PID_FILE.exists():
        console.print("[dim]Proxy is not running.[/dim]")
        return

    try:
        info = json.loads(PID_FILE.read_text())
        pid = info["pid"]
        os.kill(pid, 0)
        console.print(
            f"[green]Proxy is running[/green]\n"
            f"  PID: {pid}\n"
            f"  Port: {info.get('port', '?')}\n"
            f"  Session: [cyan]{info.get('session_id', '?')}[/cyan]\n"
            f"  Name: {info.get('session_name', '?')}"
        )
    except ProcessLookupError:
        console.print("[yellow]Proxy PID file exists but process is dead — cleaning up.[/yellow]")
        PID_FILE.unlink(missing_ok=True)


@proxy_app.command("env")
def proxy_env(
    port: int = typer.Option(4560, "--port", "-p", help="Port the proxy is running on"),
) -> None:
    """Print shell commands to set environment variables for the proxy."""
    print(f"export ANTHROPIC_BASE_URL=http://localhost:{port}")
    print(f"export OPENAI_BASE_URL=http://localhost:{port}")


def main() -> None:
    """Entry point for the Culpa CLI."""
    app()


if __name__ == "__main__":
    main()
