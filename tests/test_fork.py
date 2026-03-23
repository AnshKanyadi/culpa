"""
Tests for the PrismoForker.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk"))

import pytest

from prismo.recorder import PrismoRecorder
from prismo.fork import PrismoForker
from prismo.models import LLMCallEvent, ForkResult


def make_session():
    r = PrismoRecorder()
    r.start_session("Fork test session")
    r.record_llm_call(
        model="claude",
        messages=[{"role": "user", "content": "Fix auth bug"}],
        response_content="I'll use argon2 for hashing.",
        token_usage={"input_tokens": 50, "output_tokens": 20},
    )
    r.record_file_change(
        "src/auth.py",
        "modify",
        before_content="import bcrypt",
        after_content="import argon2",
    )
    r.record_terminal_command("pytest", stdout="3 passed", exit_code=0)
    return r.end_session()


def test_fork_at_valid_event():
    session = make_session()
    forker = PrismoForker(session)

    llm_event = [e for e in session.events if isinstance(e, LLMCallEvent)][0]
    result = forker.fork_at(
        event_id=llm_event.event_id,
        new_response="I'll keep using bcrypt, just fix the encoding.",
    )

    assert isinstance(result, ForkResult)
    assert result.session_id == session.session_id
    assert result.fork_point_event_id == llm_event.event_id
    assert result.injected_response == "I'll keep using bcrypt, just fix the encoding."
    assert result.fork_id is not None


def test_fork_has_original_events():
    session = make_session()
    forker = PrismoForker(session)

    llm_event = [e for e in session.events if isinstance(e, LLMCallEvent)][0]
    result = forker.fork_at(llm_event.event_id, "Alternative response")

    # Original path should have events after the fork point
    assert len(result.original_events_after) > 0


def test_fork_has_forked_events():
    session = make_session()
    forker = PrismoForker(session)

    llm_event = [e for e in session.events if isinstance(e, LLMCallEvent)][0]
    result = forker.fork_at(llm_event.event_id, "Alternative response")

    # Fork should have at least the injected LLM event
    assert len(result.forked_events) > 0
    assert isinstance(result.forked_events[0], LLMCallEvent)
    assert result.forked_events[0].response_content == "Alternative response"


def test_fork_invalid_event_id():
    session = make_session()
    forker = PrismoForker(session)

    with pytest.raises(ValueError, match="not found"):
        forker.fork_at("nonexistent-event-id", "response")


def test_fork_non_llm_event():
    session = make_session()
    forker = PrismoForker(session)

    from prismo.models import FileChangeEvent
    file_event = [e for e in session.events if isinstance(e, FileChangeEvent)][0]

    with pytest.raises(ValueError, match="not an LLM call"):
        forker.fork_at(file_event.event_id, "response")


def test_fork_divergence_summary():
    session = make_session()
    forker = PrismoForker(session)

    llm_event = [e for e in session.events if isinstance(e, LLMCallEvent)][0]
    result = forker.fork_at(llm_event.event_id, "Different approach")

    assert result.divergence_summary is not None
    assert len(result.divergence_summary) > 0
