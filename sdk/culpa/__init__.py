"""
Culpa — Deterministic replay & counterfactual debugging for AI agents.

Quick start:
    import culpa

    with culpa.record("Fix auth bug") as recorder:
        my_agent.run("fix the authentication bug")

Or use the global init for zero-config recording:
    culpa.init()
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from .recorder import CulpaRecorder, record, get_recorder
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
from .replay import CulpaReplayer
from .fork import CulpaForker

__version__ = "0.1.0"
__all__ = [
    "CulpaRecorder",
    "CulpaReplayer",
    "CulpaForker",
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

_global_recorder: Optional[CulpaRecorder] = None
_global_interceptors: list[Any] = []
_global_api_key: Optional[str] = None
_global_server_url: Optional[str] = None
_global_auto_upload: bool = False

CONFIG_PATH = Path.home() / ".culpa" / "config.json"
PENDING_DIR = Path.home() / ".culpa" / "pending_uploads"


def _load_config() -> dict:
    """Load configuration from ~/.culpa/config.json."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            return {}
    return {}


def _resolve_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Resolve API key from explicit arg, env var, or config file (in that order)."""
    return explicit_key or os.environ.get("CULPA_API_KEY") or _load_config().get("api_key")


def _resolve_server_url(explicit_url: Optional[str] = None) -> str:
    """Resolve server URL from explicit arg, env var, or config file, defaulting to localhost."""
    return (
        explicit_url
        or os.environ.get("CULPA_SERVER_URL")
        or _load_config().get("server_url")
        or "http://localhost:8000"
    )


def _upload_session(session: "Session", api_key: str, server_url: str) -> bool:
    """Upload a session to the server. Returns True on success."""
    try:
        import httpx
        from .utils.serialization import serialize
        response = httpx.post(
            f"{server_url}/api/sessions",
            content=serialize(session.model_dump()),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        logger.info(f"Session {session.session_id} uploaded to {server_url}")
        return True
    except Exception as e:
        logger.warning(f"Failed to upload session: {e}")
        return False


def _save_pending(session: "Session") -> None:
    """Save a session to pending uploads for retry later."""
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    from .utils.serialization import serialize
    path = PENDING_DIR / f"{session.session_id}.json"
    path.write_text(serialize(session.model_dump()))
    logger.info(f"Session saved for later upload: {path}")


def retry_pending_uploads() -> int:
    """Retry any pending uploads. Returns count of successful uploads."""
    if not PENDING_DIR.exists():
        return 0
    api_key = _resolve_api_key()
    server_url = _resolve_server_url()
    if not api_key:
        return 0

    uploaded = 0
    for path in PENDING_DIR.glob("*.json"):
        try:
            import httpx
            response = httpx.post(
                f"{server_url}/api/sessions",
                content=path.read_text(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            path.unlink()
            uploaded += 1
        except Exception:
            continue
    return uploaded


def init(
    session_name: str = "culpa-session",
    metadata: Optional[dict[str, Any]] = None,
    intercept_anthropic: bool = True,
    intercept_openai: bool = True,
    watch_directory: Optional[str] = None,
    api_key: Optional[str] = None,
    auto_upload: Optional[bool] = None,
    server_url: Optional[str] = None,
) -> CulpaRecorder:
    """
    Initialize Culpa with zero-config recording.

    Automatically intercepts LLM calls from Anthropic and OpenAI SDKs.

    Args:
        session_name: Name for the recording session.
        metadata: Optional metadata dict.
        intercept_anthropic: Whether to intercept Anthropic SDK calls.
        intercept_openai: Whether to intercept OpenAI SDK calls.
        watch_directory: Optional directory to watch for file changes.

    Returns:
        The active CulpaRecorder instance.

    Example:
        import culpa
        culpa.init()
        # All LLM calls are now recorded automatically
    """
    global _global_recorder, _global_interceptors, _global_api_key, _global_server_url, _global_auto_upload

    resolved_key = _resolve_api_key(api_key)
    _global_api_key = resolved_key
    _global_server_url = _resolve_server_url(server_url)
    _global_auto_upload = auto_upload if auto_upload is not None else (resolved_key is not None)

    recorder = CulpaRecorder()
    recorder.start_session(session_name, metadata=metadata)
    _global_recorder = recorder
    _global_interceptors = []

    if resolved_key:
        try:
            retry_pending_uploads()
        except Exception:
            pass

    if intercept_anthropic:
        try:
            from .interceptors.anthropic import AnthropicInterceptor
            interceptor = AnthropicInterceptor(recorder)
            interceptor.install()
            _global_interceptors.append(interceptor)
            logger.debug("Anthropic interceptor installed via culpa.init()")
        except Exception as e:
            logger.debug(f"Could not install Anthropic interceptor: {e}")

    if intercept_openai:
        try:
            from .interceptors.openai import OpenAIInterceptor
            interceptor = OpenAIInterceptor(recorder)
            interceptor.install()
            _global_interceptors.append(interceptor)
            logger.debug("OpenAI interceptor installed via culpa.init()")
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

    if os.environ.get("CULPA_RECORD_OUTPUT"):
        import atexit
        atexit.register(_auto_stop)

    logger.info(f"Culpa initialized — session {recorder.session_id}")
    return recorder


def _auto_stop() -> None:
    """atexit hook — ensures the session is saved when running under `culpa record`."""
    if _global_recorder is not None:
        stop()


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

    record_output = os.environ.get("CULPA_RECORD_OUTPUT")
    if record_output and session:
        try:
            from .utils.serialization import serialize
            Path(record_output).parent.mkdir(parents=True, exist_ok=True)
            Path(record_output).write_text(serialize(session.model_dump()))
            logger.debug(f"Session written to handoff file: {record_output}")
        except Exception as e:
            logger.warning(f"Failed to write handoff file: {e}")

    no_auto = os.environ.get("CULPA_NO_AUTO_UPLOAD")
    if _global_auto_upload and _global_api_key and session and not no_auto:
        success = _upload_session(session, _global_api_key, _global_server_url or "http://localhost:8000")
        if not success:
            _save_pending(session)

    return session
