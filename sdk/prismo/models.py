"""
Pydantic models for all Prismo events and session data.

These models represent the complete data captured during an AI agent session,
including LLM calls, tool invocations, file changes, and terminal commands.
"""

from __future__ import annotations

import difflib
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EventType(str, Enum):
    """Types of events that can be recorded in a Prismo session."""

    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    FILE_CHANGE = "file_change"
    TERMINAL_CMD = "terminal_cmd"


class FileOperation(str, Enum):
    """Types of file operations that can be recorded."""

    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


class SessionStatus(str, Enum):
    """Status of a Prismo session."""

    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class TokenUsage(BaseModel):
    """Token usage statistics for an LLM call."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output)."""
        return self.input_tokens + self.output_tokens


class LLMParameters(BaseModel):
    """Parameters used for an LLM call."""

    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stop_sequences: Optional[list[str]] = None
    tools: Optional[list[dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    extra: dict[str, Any] = Field(default_factory=dict)


class ToolCallRecord(BaseModel):
    """A single tool call made during an LLM response."""

    tool_call_id: str
    tool_name: str
    input_arguments: dict[str, Any]
    output_result: Optional[Any] = None
    error: Optional[str] = None


class Message(BaseModel):
    """A single message in an LLM conversation."""

    role: str  # "user", "assistant", "system", "tool"
    content: Union[str, list[dict[str, Any]]]
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


# ---------------------------------------------------------------------------
# Event models
# ---------------------------------------------------------------------------


class BaseEvent(BaseModel):
    """Base class for all Prismo events."""

    event_id: str
    event_type: EventType
    timestamp: datetime
    sequence: int
    parent_event_id: Optional[str] = None
    session_id: str


class LLMCallEvent(BaseEvent):
    """
    Records a single LLM API call with full request/response fidelity.

    Captures the complete prompt, response, timing, and token usage
    needed to deterministically replay the call.
    """

    event_type: EventType = EventType.LLM_CALL

    # Request data
    model: str
    messages: list[Message]
    parameters: LLMParameters = Field(default_factory=LLMParameters)
    system_prompt: Optional[str] = None

    # Response data
    response_content: str
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    stop_reason: Optional[str] = None
    tool_calls_made: list[ToolCallRecord] = Field(default_factory=list)

    # Timing
    latency_ms: float = 0.0
    request_start: Optional[datetime] = None
    first_token_at: Optional[datetime] = None
    request_end: Optional[datetime] = None

    # Raw response stored for exact replay
    raw_response: Optional[dict[str, Any]] = None

    @property
    def had_error(self) -> bool:
        """Whether this LLM call encountered an error."""
        return self.stop_reason == "error"

    @property
    def description(self) -> str:
        """Human-readable description of this event."""
        return f"Called {self.model} ({self.token_usage.total_tokens} tokens)"


class ToolCallEvent(BaseEvent):
    """
    Records a tool invocation made by an AI agent.

    Captures the tool name, arguments, output, and any side effects
    produced by the tool execution.
    """

    event_type: EventType = EventType.TOOL_CALL

    tool_name: str
    input_arguments: dict[str, Any]
    output_result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    side_effects: list[str] = Field(default_factory=list)  # event_ids of side effects

    @property
    def had_error(self) -> bool:
        """Whether this tool call encountered an error."""
        return self.error is not None

    @property
    def description(self) -> str:
        """Human-readable description of this event."""
        return f"Tool: {self.tool_name}"


class FileChangeEvent(BaseEvent):
    """
    Records a file system change that occurred during an agent session.

    Captures the full before/after content and computed diff for
    deterministic replay of file state.
    """

    event_type: EventType = EventType.FILE_CHANGE

    file_path: str
    operation: FileOperation
    content_before: Optional[str] = None  # None for CREATE operations
    content_after: Optional[str] = None   # None for DELETE operations
    diff: Optional[str] = None            # Unified diff string

    triggering_llm_call_id: Optional[str] = None  # Which LLM call caused this

    @model_validator(mode="after")
    def compute_diff(self) -> FileChangeEvent:
        """Auto-compute unified diff if not provided."""
        if self.diff is None and self.content_before is not None and self.content_after is not None:
            before_lines = self.content_before.splitlines(keepends=True)
            after_lines = self.content_after.splitlines(keepends=True)
            self.diff = "".join(
                difflib.unified_diff(
                    before_lines,
                    after_lines,
                    fromfile=f"a/{self.file_path}",
                    tofile=f"b/{self.file_path}",
                )
            )
        return self

    @property
    def had_error(self) -> bool:
        """File changes don't have errors per se."""
        return False

    @property
    def description(self) -> str:
        """Human-readable description of this event."""
        return f"{self.operation.value.capitalize()} {self.file_path}"


class TerminalCommandEvent(BaseEvent):
    """
    Records a terminal command executed during an agent session.

    Captures the command, working directory, stdout/stderr, and exit code
    for deterministic replay.
    """

    event_type: EventType = EventType.TERMINAL_CMD

    command: str
    working_directory: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0

    @property
    def had_error(self) -> bool:
        """Whether this command exited with a non-zero exit code."""
        return self.exit_code != 0

    @property
    def description(self) -> str:
        """Human-readable description of this event."""
        # Truncate long commands for display
        cmd_preview = self.command[:60] + "..." if len(self.command) > 60 else self.command
        return f"$ {cmd_preview}"


# Union type for all events
AnyEvent = Union[LLMCallEvent, ToolCallEvent, FileChangeEvent, TerminalCommandEvent]


# ---------------------------------------------------------------------------
# Session models
# ---------------------------------------------------------------------------


class SessionSummary(BaseModel):
    """Auto-generated summary statistics for a session."""

    total_llm_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0

    files_created: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    files_touched: list[str] = Field(default_factory=list)

    tool_calls: int = 0
    terminal_commands: int = 0
    error_count: int = 0

    models_used: list[str] = Field(default_factory=list)


class Session(BaseModel):
    """
    A complete recorded Prismo session.

    Contains all events captured during an AI agent's execution,
    plus metadata and summary statistics.
    """

    session_id: str
    name: str
    status: SessionStatus = SessionStatus.RECORDING
    metadata: dict[str, Any] = Field(default_factory=dict)

    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_ms: Optional[float] = None

    events: list[AnyEvent] = Field(default_factory=list)
    summary: SessionSummary = Field(default_factory=SessionSummary)

    def compute_summary(self) -> SessionSummary:
        """Compute and update the session summary from events."""
        summary = SessionSummary()
        models_seen: set[str] = set()
        files_touched: set[str] = set()

        # Cost per 1M tokens (approximate, Claude claude-sonnet-4-6 pricing)
        cost_per_input_token = 3.0 / 1_000_000
        cost_per_output_token = 15.0 / 1_000_000

        for event in self.events:
            if event.had_error:
                summary.error_count += 1

            if isinstance(event, LLMCallEvent):
                summary.total_llm_calls += 1
                summary.total_input_tokens += event.token_usage.input_tokens
                summary.total_output_tokens += event.token_usage.output_tokens
                summary.estimated_cost_usd += (
                    event.token_usage.input_tokens * cost_per_input_token
                    + event.token_usage.output_tokens * cost_per_output_token
                )
                models_seen.add(event.model)

            elif isinstance(event, ToolCallEvent):
                summary.tool_calls += 1

            elif isinstance(event, FileChangeEvent):
                files_touched.add(event.file_path)
                if event.operation == FileOperation.CREATE:
                    summary.files_created += 1
                elif event.operation == FileOperation.MODIFY:
                    summary.files_modified += 1
                elif event.operation == FileOperation.DELETE:
                    summary.files_deleted += 1

            elif isinstance(event, TerminalCommandEvent):
                summary.terminal_commands += 1

        summary.models_used = sorted(models_seen)
        summary.files_touched = sorted(files_touched)
        self.summary = summary
        return summary


# ---------------------------------------------------------------------------
# Fork models
# ---------------------------------------------------------------------------


class ForkRequest(BaseModel):
    """Request to fork a session at a specific event."""

    fork_point_event_id: str
    injected_response: str
    injected_tool_calls: list[ToolCallRecord] = Field(default_factory=list)


class ForkResult(BaseModel):
    """Result of a fork operation."""

    fork_id: str
    session_id: str
    fork_point_event_id: str

    original_events_after: list[AnyEvent] = Field(default_factory=list)
    forked_events: list[AnyEvent] = Field(default_factory=list)

    injected_response: str
    created_at: datetime

    divergence_summary: Optional[str] = None
    file_diffs: dict[str, str] = Field(default_factory=dict)  # file_path -> diff
