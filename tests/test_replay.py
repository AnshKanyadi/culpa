"""
Tests for the PrismoReplayer.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk"))

import pytest
from datetime import datetime, timezone, timedelta

from prismo.recorder import PrismoRecorder
from prismo.replay import PrismoReplayer, ReplayDivergenceError
from prismo.models import LLMCallEvent, FileChangeEvent


def make_session_with_events():
    """Create a session with several events for testing replay."""
    r = PrismoRecorder()
    r.start_session("Replay test session")

    r.record_llm_call(
        model="claude-sonnet-4-6-20251001",
        messages=[{"role": "user", "content": "Fix the bug"}],
        response_content="I'll look at the code first.",
        token_usage={"input_tokens": 50, "output_tokens": 20},
        latency_ms=1000.0,
    )
    r.record_tool_call("read_file", {"path": "src/main.py"}, output="def main(): pass")
    r.record_llm_call(
        model="claude-sonnet-4-6-20251001",
        messages=[{"role": "user", "content": "Fix the bug"}, {"role": "assistant", "content": "code"}],
        response_content="Found the bug. Fixing now.",
        token_usage={"input_tokens": 100, "output_tokens": 30},
        latency_ms=1500.0,
    )
    r.record_file_change("src/main.py", "modify", "def main(): pass", "def main(): return 42")
    r.record_terminal_command("pytest", stdout="1 passed", exit_code=0)

    return r.end_session()


def test_replay_iterates_all_events():
    session = make_session_with_events()
    replayer = PrismoReplayer(session)

    events = list(replayer.replay(speed=0))  # speed=0 means no delays
    assert len(events) == 5


def test_replay_preserves_order():
    session = make_session_with_events()
    replayer = PrismoReplayer(session)

    events = list(replayer.replay(speed=0))
    sequences = [e.sequence for e in events]
    assert sequences == sorted(sequences)


def test_replay_event_types():
    session = make_session_with_events()
    replayer = PrismoReplayer(session)

    events = list(replayer.replay(speed=0))
    types = [e.event_type.value for e in events]
    assert types == ["llm_call", "tool_call", "llm_call", "file_change", "terminal_cmd"]


def test_get_file_state_at():
    session = make_session_with_events()
    replayer = PrismoReplayer(session)

    # Before file change (sequence 4)
    content_before = replayer.get_file_state_at("src/main.py", sequence=3)
    assert content_before is None  # File hasn't been recorded yet

    # After file change (sequence 4 = modify event)
    content_after = replayer.get_file_state_at("src/main.py", sequence=5)
    assert content_after == "def main(): return 42"


def test_events_from():
    session = make_session_with_events()
    replayer = PrismoReplayer(session)

    # Get the first LLM call event ID
    first_llm = [e for e in session.events if isinstance(e, LLMCallEvent)][0]
    events_from = replayer.events_from(first_llm.event_id)

    assert len(events_from) == 5  # All events from first onward
    assert events_from[0].event_id == first_llm.event_id


def test_mock_response_structure():
    session = make_session_with_events()
    replayer = PrismoReplayer(session)

    # Simulate what happens when an interceptor calls _get_next_llm_response
    mock_resp = replayer._get_next_llm_response({"model": "claude-sonnet-4-6-20251001", "messages": []})
    assert hasattr(mock_resp, "content")
    assert hasattr(mock_resp, "usage")
    assert hasattr(mock_resp, "stop_reason")


def test_replay_divergence_detection():
    session = make_session_with_events()
    replayer = PrismoReplayer(session)

    # Exhaust all LLM responses
    for _ in range(2):  # Only 2 LLM calls in session
        replayer._get_next_llm_response({})

    # Next call should raise
    with pytest.raises(ReplayDivergenceError):
        replayer._get_next_llm_response({})
