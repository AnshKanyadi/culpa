"""
File system watcher for Culpa.

Monitors a working directory for file changes during an agent session,
capturing before/after content and linking changes to LLM calls.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

IGNORE_PATTERNS = {
    ".git", "__pycache__", ".pyc", ".pyo", ".pyd",
    "node_modules", ".next", "dist", "build",
    ".culpa", ".DS_Store", "*.swp", "*.swo",
}


def _should_ignore(path: str) -> bool:
    """Check if a file path should be ignored by the watcher."""
    parts = Path(path).parts
    for part in parts:
        if part in IGNORE_PATTERNS:
            return True
        if part.startswith(".") and part != ".":
            return True
    return any(path.endswith(ext) for ext in (".pyc", ".pyo", ".swp", ".swo"))


def _read_file_safe(path: str) -> Optional[str]:
    """Safely read a file, returning None if it cannot be read as text."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (OSError, PermissionError):
        return None


class FileSystemWatcher:
    """
    Monitors a directory for file system changes during a Culpa session.

    Uses watchdog if available, falls back to polling.
    Captures full file content before and after each change.

    Usage:
        watcher = FileSystemWatcher("/path/to/project", recorder)
        watcher.start()
        # ... agent makes file changes ...
        watcher.stop()
    """

    def __init__(self, watch_directory: str, recorder: Any) -> None:
        """
        Args:
            watch_directory: Root directory to monitor.
            recorder: CulpaRecorder instance to record file changes into.
        """
        self._directory = os.path.abspath(watch_directory)
        self._recorder = recorder
        self._observer: Optional[Any] = None
        self._running = False
        self._file_snapshots: dict[str, Optional[str]] = {}
        self._lock = threading.Lock()

    def _snapshot_directory(self) -> None:
        """Take a snapshot of all current files in the directory."""
        for root, dirs, files in os.walk(self._directory):
            dirs[:] = [d for d in dirs if not _should_ignore(d)]
            for filename in files:
                filepath = os.path.join(root, filename)
                if not _should_ignore(filepath):
                    content = _read_file_safe(filepath)
                    self._file_snapshots[filepath] = content

    def start(self) -> None:
        """Start watching the directory."""
        self._snapshot_directory()

        try:
            self._start_watchdog()
        except ImportError:
            logger.info("watchdog not installed; using polling watcher")
            self._start_polling()

    def _start_watchdog(self) -> None:
        """Start watchdog-based file monitoring."""
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        recorder = self._recorder
        snapshots = self._file_snapshots
        directory = self._directory
        lock = self._lock

        class CulpaEventHandler(FileSystemEventHandler):
            def on_created(self, event: Any) -> None:
                if event.is_directory or _should_ignore(event.src_path):
                    return
                with lock:
                    content = _read_file_safe(event.src_path)
                    rel_path = os.path.relpath(event.src_path, directory)
                    snapshots[event.src_path] = content
                    if recorder.is_recording and content is not None:
                        recorder.record_file_change(
                            path=rel_path,
                            operation="create",
                            before_content=None,
                            after_content=content,
                        )

            def on_modified(self, event: Any) -> None:
                if event.is_directory or _should_ignore(event.src_path):
                    return
                with lock:
                    before = snapshots.get(event.src_path)
                    after = _read_file_safe(event.src_path)
                    if after is None or before == after:
                        return
                    rel_path = os.path.relpath(event.src_path, directory)
                    snapshots[event.src_path] = after
                    if recorder.is_recording:
                        recorder.record_file_change(
                            path=rel_path,
                            operation="modify",
                            before_content=before,
                            after_content=after,
                        )

            def on_deleted(self, event: Any) -> None:
                if event.is_directory or _should_ignore(event.src_path):
                    return
                with lock:
                    before = snapshots.pop(event.src_path, None)
                    rel_path = os.path.relpath(event.src_path, directory)
                    if recorder.is_recording:
                        recorder.record_file_change(
                            path=rel_path,
                            operation="delete",
                            before_content=before,
                            after_content=None,
                        )

            def on_moved(self, event: Any) -> None:
                if event.is_directory:
                    return
                self.on_deleted(type("E", (), {"is_directory": False, "src_path": event.src_path})())
                self.on_created(type("E", (), {"is_directory": False, "src_path": event.dest_path})())

        self._observer = Observer()
        self._observer.schedule(CulpaEventHandler(), self._directory, recursive=True)
        self._observer.start()
        self._running = True
        logger.debug(f"watchdog observer started on {self._directory}")

    def _start_polling(self) -> None:
        """Start polling-based file monitoring as fallback."""
        self._running = True

        def poll_loop() -> None:
            while self._running:
                with self._lock:
                    self._check_for_changes()
                time.sleep(0.5)

        thread = threading.Thread(target=poll_loop, daemon=True)
        thread.start()
        logger.debug(f"Polling watcher started on {self._directory}")

    def _check_for_changes(self) -> None:
        """Check for file changes by comparing to snapshots."""
        current_files: dict[str, Optional[str]] = {}

        for root, dirs, files in os.walk(self._directory):
            dirs[:] = [d for d in dirs if not _should_ignore(d)]
            for filename in files:
                filepath = os.path.join(root, filename)
                if not _should_ignore(filepath):
                    current_files[filepath] = _read_file_safe(filepath)

        for filepath, content in current_files.items():
            rel_path = os.path.relpath(filepath, self._directory)
            if filepath not in self._file_snapshots:
                self._file_snapshots[filepath] = content
                if self._recorder.is_recording and content is not None:
                    self._recorder.record_file_change(
                        path=rel_path,
                        operation="create",
                        before_content=None,
                        after_content=content,
                    )
            elif self._file_snapshots[filepath] != content and content is not None:
                before = self._file_snapshots[filepath]
                self._file_snapshots[filepath] = content
                if self._recorder.is_recording:
                    self._recorder.record_file_change(
                        path=rel_path,
                        operation="modify",
                        before_content=before,
                        after_content=content,
                    )

        for filepath in list(self._file_snapshots.keys()):
            if filepath not in current_files:
                before = self._file_snapshots.pop(filepath)
                rel_path = os.path.relpath(filepath, self._directory)
                if self._recorder.is_recording:
                    self._recorder.record_file_change(
                        path=rel_path,
                        operation="delete",
                        before_content=before,
                        after_content=None,
                    )

    def stop(self) -> None:
        """Stop watching the directory."""
        self._running = False
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        logger.debug("File system watcher stopped")
