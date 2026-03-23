"""
Anthropic SDK interceptor for Prismo.

Monkey-patches anthropic.Anthropic.messages.create to transparently capture
all LLM calls while passing through to the real API.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import patch

logger = logging.getLogger(__name__)


class AnthropicInterceptor:
    """
    Intercepts Anthropic SDK calls to record them for Prismo.

    Usage:
        interceptor = AnthropicInterceptor(recorder)
        interceptor.install()
        # ... agent runs with recording ...
        interceptor.uninstall()

    Or use as context manager:
        with AnthropicInterceptor(recorder):
            # ... agent runs ...
    """

    def __init__(self, recorder: Any) -> None:
        """
        Args:
            recorder: PrismoRecorder instance to record events into.
        """
        self._recorder = recorder
        self._original_create: Optional[Any] = None
        self._original_stream: Optional[Any] = None
        self._installed = False

    def install(self) -> None:
        """Monkey-patch the Anthropic SDK to intercept calls."""
        try:
            import anthropic
        except ImportError:
            logger.warning("anthropic package not installed; interceptor not active")
            return

        original_create = anthropic.resources.messages.Messages.create

        recorder = self._recorder

        def patched_create(self_client: Any, **kwargs: Any) -> Any:
            """Patched version of messages.create that records the call."""
            request_start = datetime.now(timezone.utc)
            start_time = time.perf_counter()

            # Extract request data
            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
            system = kwargs.get("system")
            temperature = kwargs.get("temperature")
            max_tokens = kwargs.get("max_tokens")
            tools = kwargs.get("tools")
            top_p = kwargs.get("top_p")

            parameters = {
                k: v for k, v in {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                    "tools": tools,
                }.items() if v is not None
            }

            try:
                # Make the real API call
                response = original_create(self_client, **kwargs)
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                # Extract response data
                response_content = ""
                tool_calls_made = []
                stop_reason = None
                token_usage = {}
                raw_response = None

                if hasattr(response, "content"):
                    content_parts = []
                    for block in response.content:
                        if hasattr(block, "text"):
                            content_parts.append(block.text)
                        elif hasattr(block, "type") and block.type == "tool_use":
                            tool_calls_made.append({
                                "id": getattr(block, "id", ""),
                                "name": getattr(block, "name", ""),
                                "input": getattr(block, "input", {}),
                            })
                    response_content = "\n".join(content_parts)

                if hasattr(response, "stop_reason"):
                    stop_reason = response.stop_reason

                if hasattr(response, "usage"):
                    usage = response.usage
                    token_usage = {
                        "input_tokens": getattr(usage, "input_tokens", 0),
                        "output_tokens": getattr(usage, "output_tokens", 0),
                        "cache_read_tokens": getattr(usage, "cache_read_input_tokens", 0),
                        "cache_write_tokens": getattr(usage, "cache_creation_input_tokens", 0),
                    }

                try:
                    raw_response = response.model_dump() if hasattr(response, "model_dump") else None
                except Exception:
                    raw_response = None

                # Convert messages to dicts if they're objects
                messages_dicts = []
                for msg in messages:
                    if isinstance(msg, dict):
                        messages_dicts.append(msg)
                    elif hasattr(msg, "model_dump"):
                        messages_dicts.append(msg.model_dump())
                    else:
                        messages_dicts.append({"role": getattr(msg, "role", "user"), "content": str(msg)})

                if recorder.is_recording:
                    recorder.record_llm_call(
                        model=model,
                        messages=messages_dicts,
                        response_content=response_content,
                        parameters=parameters,
                        token_usage=token_usage,
                        stop_reason=stop_reason,
                        tool_calls_made=tool_calls_made,
                        latency_ms=latency_ms,
                        request_start=request_start,
                        raw_response=raw_response,
                        system_prompt=system,
                    )

                return response

            except Exception as e:
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                # Record the failed call
                if recorder.is_recording:
                    recorder.record_llm_call(
                        model=model,
                        messages=messages if isinstance(messages, list) else [],
                        response_content=f"ERROR: {e}",
                        parameters=parameters,
                        stop_reason="error",
                        latency_ms=latency_ms,
                        request_start=request_start,
                    )
                raise

        self._original_create = original_create
        anthropic.resources.messages.Messages.create = patched_create
        self._installed = True
        logger.debug("Anthropic interceptor installed")

    def uninstall(self) -> None:
        """Remove the monkey-patch and restore the original Anthropic SDK."""
        if not self._installed:
            return
        try:
            import anthropic
            if self._original_create is not None:
                anthropic.resources.messages.Messages.create = self._original_create
            self._installed = False
            logger.debug("Anthropic interceptor uninstalled")
        except ImportError:
            pass

    def __enter__(self) -> AnthropicInterceptor:
        self.install()
        return self

    def __exit__(self, *args: Any) -> None:
        self.uninstall()
