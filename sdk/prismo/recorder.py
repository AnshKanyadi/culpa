"""
Core recording engine for Prismo.

The PrismoRecorder captures every LLM call, tool invocation, file change,
and terminal command during an AI agent session with full fidelity.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator, Optional

from .models import (
    AnyEvent,
    FileChangeEvent,
    FileOperation,
    LLMCallEvent,
    LLMParameters,
    Message,
    Session,
    SessionStatus,
    SessionSummary,
    TerminalCommandEvent,
    ToolCallEvent,
    ToolCallRecord,
    TokenUsage,
)
from .utils.ids import generate_ulid

logger = logging.getLogger(__name__)


class PrismoRecorder:
    """
    Records an AI agent session with full fidelity.

    Captures LLM calls, tool invocations, file I/O, and terminal commands.
    Thread-safe for use in multi-threaded agent frameworks.

    Usage:
        recorder = PrismoRecorder()
        session_id = recorder.start_session("Fix auth bug")
        # ... agent runs ...
        session = recorder.end_session()
    """

    def __init__(self) -> None:
        self._session: Optional[Session] = None
        self._sequence: int = 0
        self._lock = threading.Lock()
        self._current_llm_call_id: Optional[str] = None

    # -----------------------------------------------------------------------
    # Session lifecycle
    # -----------------------------------------------------------------------

    def start_session(self, name: str, metadata: Optional[dict[str, Any]] = None) -> str:
        """
        Start a new recording session.

        Args:
            name: Human-readable name for this session.
            metadata: Optional metadata dict (agent version, task description, etc.)

        Returns:
            The session_id string.
        """
        with self._lock:
            session_id = generate_ulid()
            self._session = Session(
                session_id=session_id,
                name=name,
                status=SessionStatus.RECORDING,
                metadata=metadata or {},
                started_at=datetime.now(timezone.utc),
            )
            self._sequence = 0
            self._current_llm_call_id = None
            logger.info(f"Prismo session started: {session_id} — {name!r}")
            return session_id

    def end_session(self) -> Session:
        """
        End the current recording session and return the complete session bundle.

        Returns:
            The completed Session with all events and computed summary.

        Raises:
            RuntimeError: If no session is currently active.
        """
        with self._lock:
            if self._session is None:
                raise RuntimeError("No active Prismo session. Call start_session() first.")

            now = datetime.now(timezone.utc)
            self._session.ended_at = now
            self._session.status = SessionStatus.COMPLETED

            started = self._session.started_at
            self._session.duration_ms = (now - started).total_seconds() * 1000

            self._session.compute_summary()
            session = self._session
            logger.info(
                f"Prismo session ended: {session.session_id} — "
                f"{len(session.events)} events, "
                f"{session.summary.total_llm_calls} LLM calls"
            )
            return session

    def fail_session(self, error: Optional[str] = None) -> Session:
        """Mark the session as failed and return it."""
        with self._lock:
            if self._session is None:
                raise RuntimeError("No active Prismo session.")
            self._session.status = SessionStatus.FAILED
            self._session.ended_at = datetime.now(timezone.utc)
            if error:
                self._session.metadata["error"] = error
            self._session.compute_summary()
            return self._session

    @property
    def session_id(self) -> Optional[str]:
        """The current session ID, or None if not recording."""
        return self._session.session_id if self._session else None

    @property
    def is_recording(self) -> bool:
        """Whether a session is currently active."""
        return self._session is not None and self._session.status == SessionStatus.RECORDING

    # -----------------------------------------------------------------------
    # Event recording
    # -----------------------------------------------------------------------

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    def _require_session(self) -> Session:
        if self._session is None or self._session.status != SessionStatus.RECORDING:
            raise RuntimeError("No active recording session. Call start_session() first.")
        return self._session

    def record_llm_call(
        self,
        model: str,
        messages: list[dict[str, Any]],
        response_content: str,
        parameters: Optional[dict[str, Any]] = None,
        token_usage: Optional[dict[str, int]] = None,
        stop_reason: Optional[str] = None,
        tool_calls_made: Optional[list[dict[str, Any]]] = None,
        latency_ms: float = 0.0,
        request_start: Optional[datetime] = None,
        first_token_at: Optional[datetime] = None,
        raw_response: Optional[dict[str, Any]] = None,
        parent_event_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Record an LLM API call.

        Args:
            model: Model identifier (e.g., "claude-sonnet-4-6-20251001").
            messages: List of message dicts with role/content.
            response_content: The text content of the LLM response.
            parameters: LLM parameters (temperature, top_p, etc.).
            token_usage: Dict with input_tokens, output_tokens keys.
            stop_reason: Why the LLM stopped ("end_turn", "tool_use", etc.).
            tool_calls_made: List of tool calls in the response.
            latency_ms: Total request latency in milliseconds.
            request_start: When the request was initiated.
            first_token_at: When the first token was received (streaming).
            raw_response: Full raw API response dict for exact replay.
            parent_event_id: Parent event in the decision tree.
            system_prompt: System prompt used for this call.

        Returns:
            The event_id of the recorded LLM call.
        """
        with self._lock:
            session = self._require_session()
            event_id = generate_ulid()
            now = datetime.now(timezone.utc)

            # Parse messages
            parsed_messages = []
            for msg in messages:
                content = msg.get("content", "")
                parsed_messages.append(
                    Message(
                        role=msg.get("role", "user"),
                        content=content,
                        tool_call_id=msg.get("tool_call_id"),
                        name=msg.get("name"),
                    )
                )

            # Parse parameters
            params = LLMParameters()
            if parameters:
                params = LLMParameters(
                    temperature=parameters.get("temperature"),
                    top_p=parameters.get("top_p"),
                    max_tokens=parameters.get("max_tokens"),
                    stop_sequences=parameters.get("stop_sequences"),
                    tools=parameters.get("tools"),
                    extra={
                        k: v
                        for k, v in parameters.items()
                        if k not in ("temperature", "top_p", "max_tokens", "stop_sequences", "tools")
                    },
                )

            # Parse token usage
            usage = TokenUsage()
            if token_usage:
                usage = TokenUsage(
                    input_tokens=token_usage.get("input_tokens", 0),
                    output_tokens=token_usage.get("output_tokens", 0),
                    cache_read_tokens=token_usage.get("cache_read_tokens", 0),
                    cache_write_tokens=token_usage.get("cache_write_tokens", 0),
                )

            # Parse tool calls
            tools = []
            for tc in (tool_calls_made or []):
                tools.append(
                    ToolCallRecord(
                        tool_call_id=tc.get("id", generate_ulid()),
                        tool_name=tc.get("name", ""),
                        input_arguments=tc.get("input", {}),
                        output_result=tc.get("output"),
                    )
                )

            event = LLMCallEvent(
                event_id=event_id,
                session_id=session.session_id,
                timestamp=now,
                sequence=self._next_sequence(),
                parent_event_id=parent_event_id or self._current_llm_call_id,
                model=model,
                messages=parsed_messages,
                parameters=params,
                system_prompt=system_prompt,
                response_content=response_content,
                token_usage=usage,
                stop_reason=stop_reason,
                tool_calls_made=tools,
                latency_ms=latency_ms,
                request_start=request_start,
                first_token_at=first_token_at,
                request_end=now,
                raw_response=raw_response,
            )

            session.events.append(event)
            self._current_llm_call_id = event_id
            logger.debug(f"Recorded LLM call: {model} ({usage.total_tokens} tokens)")
            return event_id

    def record_tool_call(
        self,
        tool_name: str,
        input_args: dict[str, Any],
        output: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
        side_effects: Optional[list[str]] = None,
        parent_event_id: Optional[str] = None,
    ) -> str:
        """
        Record a tool invocation.

        Args:
            tool_name: Name of the tool (e.g., "read_file", "bash").
            input_args: Arguments passed to the tool.
            output: Output returned by the tool.
            error: Error message if the tool failed.
            duration_ms: How long the tool took to execute.
            side_effects: event_ids of any side effects (file changes, commands).
            parent_event_id: Parent event ID.

        Returns:
            The event_id of the recorded tool call.
        """
        with self._lock:
            session = self._require_session()
            event_id = generate_ulid()

            event = ToolCallEvent(
                event_id=event_id,
                session_id=session.session_id,
                timestamp=datetime.now(timezone.utc),
                sequence=self._next_sequence(),
                parent_event_id=parent_event_id or self._current_llm_call_id,
                tool_name=tool_name,
                input_arguments=input_args,
                output_result=output,
                error=error,
                duration_ms=duration_ms,
                side_effects=side_effects or [],
            )

            session.events.append(event)
            logger.debug(f"Recorded tool call: {tool_name}")
            return event_id

    def record_file_change(
        self,
        path: str,
        operation: str,
        before_content: Optional[str] = None,
        after_content: Optional[str] = None,
        parent_event_id: Optional[str] = None,
    ) -> str:
        """
        Record a file system change.

        Args:
            path: File path that was changed.
            operation: "create", "modify", or "delete".
            before_content: File content before the change (None for creates).
            after_content: File content after the change (None for deletes).
            parent_event_id: Parent event ID.

        Returns:
            The event_id of the recorded file change.
        """
        with self._lock:
            session = self._require_session()
            event_id = generate_ulid()

            event = FileChangeEvent(
                event_id=event_id,
                session_id=session.session_id,
                timestamp=datetime.now(timezone.utc),
                sequence=self._next_sequence(),
                parent_event_id=parent_event_id or self._current_llm_call_id,
                file_path=path,
                operation=FileOperation(operation),
                content_before=before_content,
                content_after=after_content,
                triggering_llm_call_id=self._current_llm_call_id,
            )

            session.events.append(event)
            logger.debug(f"Recorded file change: {operation} {path}")
            return event_id

    def record_terminal_command(
        self,
        command: str,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        working_directory: Optional[str] = None,
        duration_ms: float = 0.0,
        parent_event_id: Optional[str] = None,
    ) -> str:
        """
        Record a terminal command execution.

        Args:
            command: The shell command that was run.
            stdout: Standard output from the command.
            stderr: Standard error from the command.
            exit_code: Exit code (0 = success).
            working_directory: Directory where the command ran.
            duration_ms: How long the command took.
            parent_event_id: Parent event ID.

        Returns:
            The event_id of the recorded terminal command.
        """
        with self._lock:
            session = self._require_session()
            event_id = generate_ulid()

            event = TerminalCommandEvent(
                event_id=event_id,
                session_id=session.session_id,
                timestamp=datetime.now(timezone.utc),
                sequence=self._next_sequence(),
                parent_event_id=parent_event_id or self._current_llm_call_id,
                command=command,
                working_directory=working_directory,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration_ms=duration_ms,
            )

            session.events.append(event)
            logger.debug(f"Recorded terminal command: {command[:50]}")
            return event_id

    def get_events(self) -> list[AnyEvent]:
        """Return all events in the current session."""
        if self._session is None:
            return []
        return list(self._session.events)


# ---------------------------------------------------------------------------
# Global recorder instance and context manager
# ---------------------------------------------------------------------------

_global_recorder: Optional[PrismoRecorder] = None


def get_recorder() -> Optional[PrismoRecorder]:
    """Get the global Prismo recorder instance."""
    return _global_recorder


@contextmanager
def record(
    name: str,
    metadata: Optional[dict[str, Any]] = None,
    watch_directory: Optional[str] = None,
) -> Generator[PrismoRecorder, None, None]:
    """
    Context manager for recording an AI agent session.

    Usage:
        with prismo.record("Fix auth bug") as recorder:
            # Your agent code here
            result = my_agent.run("fix the auth bug")

    Args:
        name: Session name.
        metadata: Optional metadata.
        watch_directory: Optional directory to watch for file changes.

    Yields:
        The active PrismoRecorder instance.
    """
    global _global_recorder

    recorder = PrismoRecorder()
    _global_recorder = recorder

    session_id = recorder.start_session(name, metadata)
    logger.info(f"Recording session {session_id}")

    # Start file watcher if requested
    watcher = None
    if watch_directory:
        try:
            from .watchers.filesystem import FileSystemWatcher
            watcher = FileSystemWatcher(watch_directory, recorder)
            watcher.start()
        except ImportError:
            logger.warning("watchdog not installed; file watching disabled")

    try:
        yield recorder
        recorder.end_session()
    except Exception as e:
        logger.error(f"Session failed with error: {e}")
        recorder.fail_session(str(e))
        raise
    finally:
        if watcher:
            watcher.stop()
        _global_recorder = None
