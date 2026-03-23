"""
Prismo — Deterministic replay & counterfactual debugging for AI agents.

Quick start:
    import prismo

    with prismo.record("Fix auth bug") as recorder:
        # Your agent runs here
        my_agent.run("fix the authentication bug")

Or use the global init for zero-config recording:
    prismo.init()
    # Recording starts automatically for all LLM calls
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .recorder import PrismoRecorder, record, get_recorder
from .models import (
    Session,
    SessionStatus,
    LLMCallEvent,
    ToolCallEvent,
    FileChangeEvent,
    TerminalCommandEvent,
    ForkResult,
    EventType,
    FileOperation,
)
from .replay import PrismoReplayer
from .fork import PrismoForker

__version__ = "0.1.0"
__all__ = [
    "PrismoRecorder",
    "PrismoReplayer",
    "PrismoForker",
    "record",
    "init",
    "get_recorder",
    "Session",
    "SessionStatus",
    "LLMCallEvent",
    "ToolCallEvent",
    "FileChangeEvent",
    "TerminalCommandEvent",
    "ForkResult",
    "EventType",
    "FileOperation",
]

logger = logging.getLogger(__name__)

_global_recorder: Optional[PrismoRecorder] = None
_global_interceptors: list[Any] = []


def init(
    session_name: str = "prismo-session",
    metadata: Optional[dict[str, Any]] = None,
    intercept_anthropic: bool = True,
    intercept_openai: bool = True,
    watch_directory: Optional[str] = None,
) -> PrismoRecorder:
    """
    Initialize Prismo with zero-config recording.

    Automatically intercepts LLM calls from Anthropic and OpenAI SDKs.

    Args:
        session_name: Name for the recording session.
        metadata: Optional metadata dict.
        intercept_anthropic: Whether to intercept Anthropic SDK calls.
        intercept_openai: Whether to intercept OpenAI SDK calls.
        watch_directory: Optional directory to watch for file changes.

    Returns:
        The active PrismoRecorder instance.

    Example:
        import prismo
        prismo.init()
        # All LLM calls are now recorded automatically
    """
    global _global_recorder, _global_interceptors

    recorder = PrismoRecorder()
    recorder.start_session(session_name, metadata=metadata)
    _global_recorder = recorder
    _global_interceptors = []

    if intercept_anthropic:
        try:
            from .interceptors.anthropic import AnthropicInterceptor
            interceptor = AnthropicInterceptor(recorder)
            interceptor.install()
            _global_interceptors.append(interceptor)
            logger.debug("Anthropic interceptor installed via prismo.init()")
        except Exception as e:
            logger.debug(f"Could not install Anthropic interceptor: {e}")

    if intercept_openai:
        try:
            from .interceptors.openai import OpenAIInterceptor
            interceptor = OpenAIInterceptor(recorder)
            interceptor.install()
            _global_interceptors.append(interceptor)
            logger.debug("OpenAI interceptor installed via prismo.init()")
        except Exception as e:
            logger.debug(f"Could not install OpenAI interceptor: {e}")

    if watch_directory:
        try:
            from .watchers.filesystem import FileSystemWatcher
            watcher = FileSystemWatcher(watch_directory, recorder)
            watcher.start()
            _global_interceptors.append(watcher)
        except Exception as e:
            logger.debug(f"Could not start file watcher: {e}")

    logger.info(f"Prismo initialized — session {recorder.session_id}")
    return recorder


def stop() -> Optional[Session]:
    """
    Stop recording and return the completed session.

    Returns:
        The completed Session, or None if no session was active.
    """
    global _global_recorder, _global_interceptors

    if _global_recorder is None:
        return None

    for interceptor in _global_interceptors:
        if hasattr(interceptor, "uninstall"):
            interceptor.uninstall()
        elif hasattr(interceptor, "stop"):
            interceptor.stop()

    _global_interceptors = []

    session = _global_recorder.end_session()
    _global_recorder = None
    return session
