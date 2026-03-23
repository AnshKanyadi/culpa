"""
OpenAI SDK interceptor for Prismo.

Monkey-patches openai.OpenAI.chat.completions.create to transparently capture
all LLM calls while passing through to the real API.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OpenAIInterceptor:
    """
    Intercepts OpenAI SDK calls to record them for Prismo.

    Usage:
        interceptor = OpenAIInterceptor(recorder)
        interceptor.install()
        # ... agent runs with recording ...
        interceptor.uninstall()
    """

    def __init__(self, recorder: Any) -> None:
        self._recorder = recorder
        self._original_create: Optional[Any] = None
        self._installed = False

    def install(self) -> None:
        """Monkey-patch the OpenAI SDK to intercept calls."""
        try:
            import openai
        except ImportError:
            logger.warning("openai package not installed; interceptor not active")
            return

        original_create = openai.resources.chat.completions.Completions.create
        recorder = self._recorder

        def patched_create(self_client: Any, **kwargs: Any) -> Any:
            """Patched version of chat.completions.create that records the call."""
            request_start = datetime.now(timezone.utc)
            start_time = time.perf_counter()

            model = kwargs.get("model", "unknown")
            messages = kwargs.get("messages", [])
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
                response = original_create(self_client, **kwargs)
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                response_content = ""
                tool_calls_made = []
                stop_reason = None
                token_usage = {}

                if hasattr(response, "choices") and response.choices:
                    choice = response.choices[0]
                    msg = choice.message
                    response_content = msg.content or ""
                    stop_reason = choice.finish_reason

                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            import json
                            try:
                                args = json.loads(tc.function.arguments)
                            except Exception:
                                args = {"raw": tc.function.arguments}
                            tool_calls_made.append({
                                "id": tc.id,
                                "name": tc.function.name,
                                "input": args,
                            })

                if hasattr(response, "usage") and response.usage:
                    token_usage = {
                        "input_tokens": response.usage.prompt_tokens,
                        "output_tokens": response.usage.completion_tokens,
                    }

                # System prompt is typically first message with role="system"
                system_prompt = None
                messages_filtered = []
                for msg in messages:
                    if isinstance(msg, dict):
                        if msg.get("role") == "system":
                            system_prompt = msg.get("content", "")
                        else:
                            messages_filtered.append(msg)
                    else:
                        messages_filtered.append(msg)

                if recorder.is_recording:
                    recorder.record_llm_call(
                        model=model,
                        messages=messages_filtered,
                        response_content=response_content,
                        parameters=parameters,
                        token_usage=token_usage,
                        stop_reason=stop_reason,
                        tool_calls_made=tool_calls_made,
                        latency_ms=latency_ms,
                        request_start=request_start,
                        system_prompt=system_prompt,
                    )

                return response

            except Exception as e:
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

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
        openai.resources.chat.completions.Completions.create = patched_create
        self._installed = True
        logger.debug("OpenAI interceptor installed")

    def uninstall(self) -> None:
        """Remove the monkey-patch and restore the original OpenAI SDK."""
        if not self._installed:
            return
        try:
            import openai
            if self._original_create is not None:
                openai.resources.chat.completions.Completions.create = self._original_create
            self._installed = False
            logger.debug("OpenAI interceptor uninstalled")
        except ImportError:
            pass

    def __enter__(self) -> OpenAIInterceptor:
        self.install()
        return self

    def __exit__(self, *args: Any) -> None:
        self.uninstall()
