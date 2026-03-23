"""
Counterfactual fork engine for Prismo.

Allows forking a session at a specific decision node, injecting a different
LLM response, and observing what would have happened downstream.
"""

from __future__ import annotations

import difflib
import logging
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import (
    AnyEvent,
    FileChangeEvent,
    ForkRequest,
    ForkResult,
    LLMCallEvent,
    Session,
    ToolCallEvent,
    ToolCallRecord,
)
from .replay import PrismoReplayer
from .utils.ids import generate_ulid

logger = logging.getLogger(__name__)


class PrismoForker:
    """
    Forks a session at a specific event, injecting a different LLM response.

    The fork operation works in three phases:
    1. PRE-FORK: Replay deterministically up to the fork point using recorded data
    2. AT FORK: Inject the user-provided alternative response
    3. POST-FORK: Execute live (or simulate) from the fork point onward

    For the MVP, post-fork execution is simulated rather than running live agents.

    Usage:
        forker = PrismoForker(session)
        result = forker.fork_at(
            event_id="01HNXXX...",
            new_response="I should use bcrypt instead of argon2"
        )
        print(result.divergence_summary)
    """

    def __init__(self, session: Session) -> None:
        """
        Args:
            session: The recorded Session to fork from.
        """
        self._session = session
        self._replayer = PrismoReplayer(session)

    def fork_at(
        self,
        event_id: str,
        new_response: str,
        injected_tool_calls: Optional[list[dict[str, Any]]] = None,
    ) -> ForkResult:
        """
        Fork the session at a specific event, injecting a different LLM response.

        Args:
            event_id: The event_id of the LLM call to fork at.
            new_response: The alternative LLM response to inject.
            injected_tool_calls: Optional alternative tool calls to inject.

        Returns:
            ForkResult containing the original and forked event traces.

        Raises:
            ValueError: If the event_id is not found or not an LLM call.
        """
        # Find the fork point event
        fork_event = self._find_event(event_id)
        if fork_event is None:
            raise ValueError(f"Event {event_id!r} not found in session")
        if not isinstance(fork_event, LLMCallEvent):
            raise ValueError(f"Event {event_id!r} is not an LLM call event (type: {fork_event.event_type})")

        fork_id = generate_ulid()
        logger.info(f"Creating fork {fork_id} at event {event_id}")

        # Get events before the fork point (for deterministic replay context)
        events_before = [e for e in self._session.events if e.sequence < fork_event.sequence]

        # Get original events AFTER the fork point
        original_events_after = [
            e for e in self._session.events if e.sequence > fork_event.sequence
        ]

        # Create the forked events (simulated post-fork execution)
        forked_events = self._simulate_fork(
            fork_event=fork_event,
            new_response=new_response,
            injected_tool_calls=injected_tool_calls or [],
            original_events_after=original_events_after,
        )

        # Compute file diffs between original and forked outcomes
        file_diffs = self._compute_outcome_diffs(
            original_events=original_events_after,
            forked_events=forked_events,
        )

        # Generate divergence summary
        divergence_summary = self._summarize_divergence(
            original_events=original_events_after,
            forked_events=forked_events,
        )

        result = ForkResult(
            fork_id=fork_id,
            session_id=self._session.session_id,
            fork_point_event_id=event_id,
            original_events_after=original_events_after,
            forked_events=forked_events,
            injected_response=new_response,
            created_at=datetime.now(timezone.utc),
            divergence_summary=divergence_summary,
            file_diffs=file_diffs,
        )

        return result

    def _find_event(self, event_id: str) -> Optional[AnyEvent]:
        """Find an event by its ID in the session."""
        for event in self._session.events:
            if event.event_id == event_id:
                return event
        return None

    def _simulate_fork(
        self,
        fork_event: LLMCallEvent,
        new_response: str,
        injected_tool_calls: list[dict[str, Any]],
        original_events_after: list[AnyEvent],
    ) -> list[AnyEvent]:
        """
        Simulate the post-fork execution by creating plausible forked events.

        In a full implementation, this would:
        1. Restore the filesystem to the state at the fork point
        2. Make a live LLM call with the injected response (or use it as the response)
        3. Execute the downstream agent loop with live API calls

        For the MVP, we create a modified version of the original events
        that reflects the injected response change.
        """
        forked_events = []
        now = datetime.now(timezone.utc)

        # Create a modified version of the fork event with the new response
        forked_llm_event = LLMCallEvent(
            event_id=generate_ulid(),
            session_id=self._session.session_id,
            timestamp=now,
            sequence=fork_event.sequence,
            parent_event_id=fork_event.parent_event_id,
            model=fork_event.model,
            messages=fork_event.messages,
            parameters=fork_event.parameters,
            system_prompt=fork_event.system_prompt,
            response_content=new_response,
            token_usage=fork_event.token_usage,
            stop_reason=fork_event.stop_reason,
            tool_calls_made=[
                ToolCallRecord(
                    tool_call_id=tc.get("id", generate_ulid()),
                    tool_name=tc.get("name", ""),
                    input_arguments=tc.get("input", {}),
                )
                for tc in injected_tool_calls
            ],
            latency_ms=fork_event.latency_ms,
        )
        forked_events.append(forked_llm_event)

        # For events after the fork, we keep the structure but mark them as forked
        # In a real implementation, these would be the result of live execution
        # with the new response. For the MVP, we include modified versions.
        for i, event in enumerate(original_events_after):
            forked_event = event.model_copy(
                update={
                    "event_id": generate_ulid(),
                    "session_id": self._session.session_id,
                    "parent_event_id": forked_llm_event.event_id if i == 0 else None,
                }
            )
            forked_events.append(forked_event)

        return forked_events

    def _compute_outcome_diffs(
        self,
        original_events: list[AnyEvent],
        forked_events: list[AnyEvent],
    ) -> dict[str, str]:
        """Compute diffs between the file states in original vs forked outcomes."""
        diffs: dict[str, str] = {}

        # Gather final file contents from original events
        original_files: dict[str, Optional[str]] = {}
        for event in original_events:
            if isinstance(event, FileChangeEvent):
                original_files[event.file_path] = event.content_after

        # Gather final file contents from forked events
        forked_files: dict[str, Optional[str]] = {}
        for event in forked_events:
            if isinstance(event, FileChangeEvent):
                forked_files[event.file_path] = event.content_after

        # Compute diffs for all files that differ
        all_paths = set(original_files.keys()) | set(forked_files.keys())
        for path in all_paths:
            orig_content = original_files.get(path) or ""
            fork_content = forked_files.get(path) or ""

            if orig_content != fork_content:
                diff = "".join(
                    difflib.unified_diff(
                        orig_content.splitlines(keepends=True),
                        fork_content.splitlines(keepends=True),
                        fromfile=f"original/{path}",
                        tofile=f"forked/{path}",
                    )
                )
                if diff:
                    diffs[path] = diff

        return diffs

    def _summarize_divergence(
        self,
        original_events: list[AnyEvent],
        forked_events: list[AnyEvent],
    ) -> str:
        """Generate a human-readable summary of how the two paths diverge."""
        orig_llm = sum(1 for e in original_events if isinstance(e, LLMCallEvent))
        fork_llm = sum(1 for e in forked_events if isinstance(e, LLMCallEvent))

        orig_files = set(
            e.file_path for e in original_events if isinstance(e, FileChangeEvent)
        )
        fork_files = set(
            e.file_path for e in forked_events if isinstance(e, FileChangeEvent)
        )

        lines = [
            f"Original path: {len(original_events)} events, {orig_llm} LLM calls, {len(orig_files)} files changed",
            f"Forked path: {len(forked_events)} events, {fork_llm} LLM calls, {len(fork_files)} files changed",
        ]

        files_only_in_orig = orig_files - fork_files
        files_only_in_fork = fork_files - orig_files
        if files_only_in_orig:
            lines.append(f"Files changed only in original: {', '.join(sorted(files_only_in_orig))}")
        if files_only_in_fork:
            lines.append(f"Files changed only in fork: {', '.join(sorted(files_only_in_fork))}")

        return "\n".join(lines)
