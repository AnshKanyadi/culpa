"""
Fork example — demonstrates counterfactual forking.

Shows how to fork a session at a specific LLM call and compare outcomes.
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk"))

from culpa.models import Session, LLMCallEvent
from culpa.fork import CulpaForker


def load_demo_session() -> Session:
    demo_path = Path.home() / ".culpa" / "sessions" / "01HCULPA00DEMO0SESSION001.json"
    if not demo_path.exists():
        sys.path.insert(0, str(Path(__file__).parent))
        from demo_session import generate_demo_session
        session = generate_demo_session()
        demo_path.parent.mkdir(parents=True, exist_ok=True)
        with open(demo_path, "w") as f:
            json.dump(session.model_dump(), f, default=str)
        return session
    with open(demo_path) as f:
        data = json.load(f)
    return Session.model_validate(data)


def main():
    session = load_demo_session()
    print(f"Session: {session.name}")
    print(f"Events: {len(session.events)}")

    # Find the LLM call where the agent decides to switch to argon2
    llm_events = [e for e in session.events if isinstance(e, LLMCallEvent)]

    # The 4th LLM call (sequence 7) is where it decides to use argon2
    # Let's fork at the 3rd LLM call (diagnosis) and inject a better response
    diagnosis_llm = llm_events[2]  # llm3 — the diagnosis event

    print(f"\n=== Forking at LLM call #{diagnosis_llm.sequence} ===")
    print(f"Original response:\n{diagnosis_llm.response_content}\n")

    better_response = """
I see the issue. The bcrypt library had a breaking change in v4.x regarding byte/string
handling. The fix is simple: we need to ensure we're comparing bytes to bytes consistently.

Let me check the bcrypt version and fix the encoding issue without switching libraries.
The existing bcrypt hashes for 12,847 production users will remain valid.
"""

    forker = CulpaForker(session)
    result = forker.fork_at(
        event_id=diagnosis_llm.event_id,
        new_response=better_response.strip(),
    )

    print(f"Fork ID: {result.fork_id}")
    print(f"\n=== Divergence Summary ===")
    print(result.divergence_summary)

    print(f"\n=== Original Path ({len(result.original_events_after)} events) ===")
    for event in result.original_events_after[:5]:
        icon = {"llm_call": "🧠", "tool_call": "🔧", "file_change": "📄", "terminal_cmd": "💻"}.get(
            event.event_type.value, "•"
        )
        print(f"  {icon} {event.description}")

    print(f"\n=== Forked Path ({len(result.forked_events)} events) ===")
    for event in result.forked_events[:5]:
        icon = {"llm_call": "🧠", "tool_call": "🔧", "file_change": "📄", "terminal_cmd": "💻"}.get(
            event.event_type.value, "•"
        )
        print(f"  {icon} {event.description}")

    if result.file_diffs:
        print(f"\n=== Files that differ between paths ===")
        for path in result.file_diffs:
            print(f"  📄 {path}")


if __name__ == "__main__":
    main()
