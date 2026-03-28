"""
Replay example — demonstrates deterministic session replay.

Shows how to:
1. Load a recorded session
2. Replay it with different speeds
3. Inspect events at specific points
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk"))

from culpa.models import Session, LLMCallEvent, FileChangeEvent, TerminalCommandEvent
from culpa.replay import CulpaReplayer


def load_demo_session() -> Session:
    """Load the demo session from disk, or generate it if not found."""
    demo_path = Path.home() / ".culpa" / "sessions" / "01HCULPA00DEMO0SESSION001.json"

    if not demo_path.exists():
        print("Demo session not found. Generating it...")
        sys.path.insert(0, str(Path(__file__).parent))
        from demo_session import generate_demo_session
        import json
        session = generate_demo_session()
        demo_path.parent.mkdir(parents=True, exist_ok=True)
        with open(demo_path, "w") as f:
            json.dump(session.model_dump(), f, default=str)
        return session

    with open(demo_path) as f:
        data = json.load(f)
    return Session.model_validate(data)


def replay_fast(session: Session):
    """Fast replay — just print each event."""
    print(f"\n=== Fast Replay: {session.name} ===")
    print(f"Total events: {len(session.events)}\n")

    replayer = CulpaReplayer(session)
    for event in replayer.replay(speed=0):  # speed=0 = no delays
        icon = {
            "llm_call": "🧠",
            "tool_call": "🔧",
            "file_change": "📄",
            "terminal_cmd": "💻",
        }.get(event.event_type.value, "•")

        if isinstance(event, LLMCallEvent):
            tokens = event.token_usage.input_tokens + event.token_usage.output_tokens
            print(f"  {icon} [{event.sequence:2d}] {event.model} — {tokens} tokens — {event.latency_ms:.0f}ms")
            print(f"       Response: {event.response_content[:80]}...")
        elif isinstance(event, FileChangeEvent):
            print(f"  {icon} [{event.sequence:2d}] {event.operation} {event.file_path}")
        elif isinstance(event, TerminalCommandEvent):
            status = "✓" if event.exit_code == 0 else "✗"
            print(f"  {icon} [{event.sequence:2d}] {status} {event.command[:60]}")
        else:
            print(f"  {icon} [{event.sequence:2d}] {event.event_type}: {event.description}")

    print(f"\nReplay complete — {len(session.events)} events")


def inspect_file_at_point(session: Session, file_path: str, at_sequence: int):
    """Show the state of a file at a specific point in the session."""
    print(f"\n=== File State at sequence {at_sequence}: {file_path} ===")

    replayer = CulpaReplayer(session)
    content = replayer.get_file_state_at(file_path, at_sequence)

    if content is None:
        print(f"File {file_path} didn't exist at sequence {at_sequence}")
    else:
        print(f"Content ({len(content)} chars):")
        print("-" * 40)
        print(content[:500])
        if len(content) > 500:
            print("... [truncated]")
        print("-" * 40)


if __name__ == "__main__":
    session = load_demo_session()
    replay_fast(session)

    # Show file state before and after the critical change
    file_events = [e for e in session.events if isinstance(e, FileChangeEvent)]
    if file_events:
        file_path = file_events[0].file_path
        change_seq = file_events[0].sequence
        inspect_file_at_point(session, file_path, change_seq - 1)
        inspect_file_at_point(session, file_path, change_seq)
