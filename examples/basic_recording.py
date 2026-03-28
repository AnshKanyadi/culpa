"""
Basic recording example — demonstrates how to instrument an AI agent session.

This example shows how to:
1. Use culpa.init() for zero-config recording
2. Use the context manager for explicit recording
3. Manually record events
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk"))

import json

import culpa


def example_zero_config():
    """Zero-config example: just call culpa.init() and all LLM calls are recorded."""
    print("\n=== Example 1: Zero-config recording ===")

    recorder = culpa.init(session_name="Zero-config demo")

    # Manually record some events to simulate agent activity
    recorder.record_llm_call(
        model="claude-sonnet-4-6-20251001",
        messages=[{"role": "user", "content": "Hello, fix this bug"}],
        response_content="Sure, I'll look at the code.",
        token_usage={"input_tokens": 25, "output_tokens": 12},
        latency_ms=850.0,
    )

    recorder.record_tool_call(
        tool_name="read_file",
        input_args={"path": "main.py"},
        output="def foo(): return 1",
        duration_ms=8.0,
    )

    recorder.record_file_change(
        path="main.py",
        operation="modify",
        before_content="def foo(): return 1",
        after_content="def foo(): return 42",
    )

    session = culpa.stop()
    print(f"Session ID: {session.session_id}")
    print(f"Events: {len(session.events)}")
    print(f"LLM calls: {session.summary.total_llm_calls}")
    print(f"Files changed: {session.summary.files_modified}")
    return session


def example_context_manager():
    """Context manager example: explicit start/stop with automatic cleanup."""
    print("\n=== Example 2: Context manager recording ===")

    with culpa.record("Context manager demo") as recorder:
        recorder.record_llm_call(
            model="gpt-4",
            messages=[{"role": "user", "content": "What files should I edit?"}],
            response_content="You should edit src/auth.py to fix the issue.",
            token_usage={"input_tokens": 30, "output_tokens": 25},
            latency_ms=1200.0,
        )

        recorder.record_terminal_command(
            command="python -m pytest tests/",
            stdout="5 passed in 1.23s",
            stderr="",
            exit_code=0,
            duration_ms=1230.0,
        )

    # Session is automatically ended when context exits
    print(f"Session recorded: {recorder.session_id}")


def example_save_to_disk():
    """Save a session to disk for later replay or upload."""
    print("\n=== Example 3: Save session to disk ===")

    recorder = CulpaRecorder()
    recorder.start_session("Save to disk demo")

    recorder.record_llm_call(
        model="claude-sonnet-4-6-20251001",
        messages=[{"role": "user", "content": "task"}],
        response_content="response",
        token_usage={"input_tokens": 10, "output_tokens": 5},
    )

    session = recorder.end_session()

    # Save to file
    output_path = Path.home() / ".culpa" / "sessions" / f"{session.session_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(session.model_dump(), f, default=str, indent=2)

    print(f"Session saved to: {output_path}")
    print(f"Run: culpa replay {session.session_id}")
    return str(output_path)


if __name__ == "__main__":
    from culpa.recorder import CulpaRecorder

    session = example_zero_config()
    example_context_manager()
    example_save_to_disk()

    print("\n✅ All examples completed successfully!")
    print(f"\nTo view sessions in the dashboard:")
    print("  1. culpa serve")
    print("  2. Open http://localhost:5173")
