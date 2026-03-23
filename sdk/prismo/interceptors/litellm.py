"""
LiteLLM interceptor for Prismo.

Monkey-patches litellm.completion to transparently capture all LLM calls.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LiteLLMInterceptor:
    """
    Intercepts LiteLLM calls to record them for Prismo.
    """

    def __init__(self, recorder: Any) -> None:
        self._recorder = recorder
        self._original_completion: Optional[Any] = None
        self._installed = False

    def install(self) -> None:
        """Monkey-patch LiteLLM to intercept calls."""
        try:
            import litellm
        except ImportError:
            logger.warning("litellm package not installed; interceptor not active")
            return

        original_completion = litellm.completion
        recorder = self._recorder

        def patched_completion(*args: Any, **kwargs: Any) -> Any:
            """Patched version of litellm.completion that records the call."""
            request_start = datetime.now(timezone.utc)
            start_time = time.perf_counter()

            model = kwargs.get("model", args[0] if args else "unknown")
            messages = kwargs.get("messages", [])
            temperature = kwargs.get("temperature")
            max_tokens = kwargs.get("max_tokens")
            top_p = kwargs.get("top_p")

            parameters = {
                k: v for k, v in {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": top_p,
                }.items() if v is not None
            }

            try:
                response = original_completion(*args, **kwargs)
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                response_content = ""
                tool_calls_made = []
                stop_reason = None
                token_usage = {}

                if hasattr(response, "choices") and response.choices:
                    choice = response.choices[0]
                    response_content = choice.message.content or ""
                    stop_reason = choice.finish_reason

                if hasattr(response, "usage") and response.usage:
                    token_usage = {
                        "input_tokens": getattr(response.usage, "prompt_tokens", 0),
                        "output_tokens": getattr(response.usage, "completion_tokens", 0),
                    }

                if recorder.is_recording:
                    recorder.record_llm_call(
                        model=str(model),
                        messages=messages if isinstance(messages, list) else [],
                        response_content=response_content,
                        parameters=parameters,
                        token_usage=token_usage,
                        stop_reason=stop_reason,
                        tool_calls_made=tool_calls_made,
                        latency_ms=latency_ms,
                        request_start=request_start,
                    )

                return response

            except Exception as e:
                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000

                if recorder.is_recording:
                    recorder.record_llm_call(
                        model=str(model),
                        messages=messages if isinstance(messages, list) else [],
                        response_content=f"ERROR: {e}",
                        parameters=parameters,
                        stop_reason="error",
                        latency_ms=latency_ms,
                        request_start=request_start,
                    )
                raise

        self._original_completion = original_completion
        litellm.completion = patched_completion
        self._installed = True
        logger.debug("LiteLLM interceptor installed")

    def uninstall(self) -> None:
        """Restore the original LiteLLM completion function."""
        if not self._installed:
            return
        try:
            import litellm
            if self._original_completion is not None:
                litellm.completion = self._original_completion
            self._installed = False
            logger.debug("LiteLLM interceptor uninstalled")
        except ImportError:
            pass

    def __enter__(self) -> LiteLLMInterceptor:
        self.install()
        return self

    def __exit__(self, *args: Any) -> None:
        self.uninstall()
