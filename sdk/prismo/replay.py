"""
Deterministic replay engine for Prismo.

Replays a recorded session using pre-recorded LLM responses as stubs,
producing identical behavior without making live API calls.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Generator, Iterator, Optional

from .models import (
    AnyEvent,
    EventType,
    LLMCallEvent,
    Session,
    TerminalCommandEvent,
    ToolCallEvent,
)

logger = logging.getLogger(__name__)


class ReplayDivergenceError(Exception):
    """Raised when the replay execution path diverges from the recording."""
    pass


class StubAnthropicClient:
    """
    A stub Anthropic client that returns pre-recorded responses during replay.

    Install this in place of the real Anthropic client to replay a session
    without making live API calls.
    """

    def __init__(self, replayer: PrismoReplayer) -> None:
        self._replayer = replayer
        self.messages = self._MessagesResource(replayer)

    class _MessagesResource:
        def __init__(self, replayer: PrismoReplayer) -> None:
            self._replayer = replayer

        def create(self, **kwargs: Any) -> Any:
            """Return the next recorded LLM response."""
            return self._replayer._get_next_llm_response(kwargs)


class PrismoReplayer:
    """
    Replays a recorded Prismo session deterministically.

    Instead of making live LLM API calls, this replayer intercepts calls
    and returns the pre-recorded responses, ensuring identical behavior.

    Usage:
        replayer = PrismoReplayer(session)
        for event in replayer.replay():
            print(f"[{event.event_type}] {event.description}")
    """

    def __init__(self, session: Session) -> None:
        """
        Args:
            session: The recorded Session to replay.
        """
        self._session = session
        self._events = sorted(session.events, key=lambda e: e.sequence)
        self._llm_call_queue: list[LLMCallEvent] = [
            e for e in self._events if isinstance(e, LLMCallEvent)
        ]
        self._llm_queue_index = 0

    @classmethod
    def from_session(cls, session: Session) -> PrismoReplayer:
        """Create a replayer from a Session object."""
        return cls(session)

    def _get_next_llm_response(self, request_kwargs: dict[str, Any]) -> Any:
        """
        Return the next pre-recorded LLM response.

        Validates that the request matches what was recorded (model, message count)
        to detect divergence.

        Args:
            request_kwargs: The kwargs from the intercepted LLM call.

        Returns:
            A mock response object with the recorded data.

        Raises:
            ReplayDivergenceError: If the request doesn't match the recording.
        """
        if self._llm_queue_index >= len(self._llm_call_queue):
            raise ReplayDivergenceError(
                f"Replay ran out of recorded LLM responses. "
                f"Got {self._llm_queue_index + 1} calls but only {len(self._llm_call_queue)} were recorded."
            )

        recorded = self._llm_call_queue[self._llm_queue_index]

        # Validate model matches
        requested_model = request_kwargs.get("model", "")
        if requested_model and recorded.model and requested_model != recorded.model:
            logger.warning(
                f"Replay divergence: requested model {requested_model!r} "
                f"but recorded model was {recorded.model!r}"
            )

        self._llm_queue_index += 1
        logger.debug(
            f"Replay: returning recorded response for LLM call {recorded.event_id} "
            f"({recorded.model})"
        )

        return self._make_mock_response(recorded)

    def _make_mock_response(self, event: LLMCallEvent) -> Any:
        """Create a mock Anthropic-like response object from a recorded event."""

        class MockTextBlock:
            def __init__(self, text: str) -> None:
                self.type = "text"
                self.text = text

        class MockToolUseBlock:
            def __init__(self, tc: Any) -> None:
                self.type = "tool_use"
                self.id = tc.tool_call_id
                self.name = tc.tool_name
                self.input = tc.input_arguments

        class MockUsage:
            def __init__(self, event: LLMCallEvent) -> None:
                self.input_tokens = event.token_usage.input_tokens
                self.output_tokens = event.token_usage.output_tokens

        class MockResponse:
            def __init__(self, event: LLMCallEvent) -> None:
                self.id = event.event_id
                self.model = event.model
                self.stop_reason = event.stop_reason
                self.usage = MockUsage(event)

                content = []
                if event.response_content:
                    content.append(MockTextBlock(event.response_content))
                for tc in event.tool_calls_made:
                    content.append(MockToolUseBlock(tc))
                self.content = content

            def model_dump(self) -> dict[str, Any]:
                return {
                    "id": self.id,
                    "model": self.model,
                    "stop_reason": self.stop_reason,
                }

        return MockResponse(event)

    def replay(
        self,
        speed: float = 1.0,
        start_sequence: int = 0,
    ) -> Iterator[AnyEvent]:
        """
        Replay the session, yielding events in order.

        Args:
            speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x speed).
            start_sequence: Sequence number to start from (for seeking).

        Yields:
            Events in chronological order.
        """
        logger.info(
            f"Starting replay of session {self._session.session_id} "
            f"({len(self._events)} events, {speed}x speed)"
        )

        prev_timestamp = None

        for event in self._events:
            if event.sequence < start_sequence:
                continue

            # Simulate timing between events
            if speed > 0 and prev_timestamp is not None:
                delay = (event.timestamp - prev_timestamp).total_seconds() / speed
                if 0 < delay < 30:  # Cap delays at 30s
                    time.sleep(delay)

            prev_timestamp = event.timestamp
            logger.debug(f"Replay: event {event.sequence} — {event.event_type} — {event.description}")
            yield event

        logger.info("Replay complete")

    def get_file_state_at(self, file_path: str, sequence: int) -> Optional[str]:
        """
        Get the content of a file as it was at a specific point in the session.

        Args:
            file_path: The relative file path.
            sequence: The sequence number to look up.

        Returns:
            File content at that point, or None if the file didn't exist.
        """
        from .models import FileChangeEvent, FileOperation

        last_content: Optional[str] = None

        for event in self._events:
            if event.sequence > sequence:
                break
            if isinstance(event, FileChangeEvent) and event.file_path == file_path:
                if event.operation == FileOperation.DELETE:
                    last_content = None
                else:
                    last_content = event.content_after

        return last_content

    def events_from(self, event_id: str) -> list[AnyEvent]:
        """Get all events after (and including) a specific event_id."""
        found = False
        result = []
        for event in self._events:
            if event.event_id == event_id:
                found = True
            if found:
                result.append(event)
        return result
