"""
Tests for the CulpaRecorder.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk"))

import pytest
from datetime import datetime, timezone

from culpa.recorder import CulpaRecorder
from culpa.models import (
    SessionStatus, LLMCallEvent, ToolCallEvent,
    FileChangeEvent, TerminalCommandEvent, FileOperation,
)


@pytest.fixture
def recorder() -> CulpaRecorder:
    r = CulpaRecorder()
    r.start_session("Test session", {"test": True})
    return r


def test_start_session():
    r = CulpaRecorder()
    session_id = r.start_session("My session", {"key": "value"})
    assert session_id is not None
    assert len(session_id) == 26  # ULID length
    assert r.is_recording
    assert r.session_id == session_id


def test_end_session(recorder):
    session = recorder.end_session()
    assert session.status == SessionStatus.COMPLETED
    assert session.ended_at is not None
    assert session.duration_ms is not None
    assert not recorder.is_recording


def test_record_llm_call(recorder):
    event_id = recorder.record_llm_call(
        model="claude-sonnet-4-6-20251001",
        messages=[{"role": "user", "content": "Hello"}],
        response_content="Hello back!",
        token_usage={"input_tokens": 10, "output_tokens": 5},
        stop_reason="end_turn",
        latency_ms=500.0,
    )
    assert event_id is not None
    events = recorder.get_events()
    assert len(events) == 1
    assert isinstance(events[0], LLMCallEvent)
    assert events[0].model == "claude-sonnet-4-6-20251001"
    assert events[0].response_content == "Hello back!"
    assert events[0].token_usage.input_tokens == 10
    assert events[0].token_usage.output_tokens == 5


def test_record_tool_call(recorder):
    event_id = recorder.record_tool_call(
        tool_name="read_file",
        input_args={"path": "test.py"},
        output="print('hello')",
        duration_ms=12.0,
    )
    events = recorder.get_events()
    assert len(events) == 1
    assert isinstance(events[0], ToolCallEvent)
    assert events[0].tool_name == "read_file"
    assert events[0].input_arguments == {"path": "test.py"}


def test_record_file_change(recorder):
    event_id = recorder.record_file_change(
        path="src/main.py",
        operation="modify",
        before_content="old code",
        after_content="new code",
    )
    events = recorder.get_events()
    assert len(events) == 1
    assert isinstance(events[0], FileChangeEvent)
    assert events[0].file_path == "src/main.py"
    assert events[0].operation == FileOperation.MODIFY
    assert events[0].diff is not None  # Auto-computed


def test_record_terminal_command(recorder):
    event_id = recorder.record_terminal_command(
        command="pytest tests/",
        stdout="3 passed",
        stderr="",
        exit_code=0,
        duration_ms=456.0,
    )
    events = recorder.get_events()
    assert len(events) == 1
    assert isinstance(events[0], TerminalCommandEvent)
    assert events[0].command == "pytest tests/"
    assert events[0].exit_code == 0


def test_sequence_numbering(recorder):
    recorder.record_tool_call("tool1", {})
    recorder.record_tool_call("tool2", {})
    recorder.record_tool_call("tool3", {})

    events = recorder.get_events()
    assert [e.sequence for e in events] == [1, 2, 3]


def test_parent_event_tracking(recorder):
    llm_id = recorder.record_llm_call(
        model="claude",
        messages=[{"role": "user", "content": "hi"}],
        response_content="hello",
    )
    tool_id = recorder.record_tool_call("read", {})

    events = recorder.get_events()
    assert events[1].parent_event_id == llm_id


def test_session_summary(recorder):
    recorder.record_llm_call(
        model="claude",
        messages=[],
        response_content="response",
        token_usage={"input_tokens": 100, "output_tokens": 50},
    )
    recorder.record_file_change("src/auth.py", "create", after_content="code")
    recorder.record_terminal_command("pytest", stdout="pass", exit_code=0)

    session = recorder.end_session()
    assert session.summary.total_llm_calls == 1
    assert session.summary.total_input_tokens == 100
    assert session.summary.total_output_tokens == 50
    assert session.summary.files_created == 1
    assert session.summary.terminal_commands == 1


def test_fail_session(recorder):
    session = recorder.fail_session("Something went wrong")
    assert session.status == SessionStatus.FAILED
    assert "error" in session.metadata


def test_require_active_session():
    r = CulpaRecorder()
    with pytest.raises(RuntimeError):
        r.record_llm_call("model", [], "response")


def test_diff_auto_computed():
    r = CulpaRecorder()
    r.start_session("test")
    r.record_file_change(
        path="test.py",
        operation="modify",
        before_content="line1\nline2\n",
        after_content="line1\nline3\n",
    )
    event = r.get_events()[0]
    assert isinstance(event, FileChangeEvent)
    assert "line2" in (event.diff or "")
    assert "line3" in (event.diff or "")
