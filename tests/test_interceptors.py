"""
Tests for LLM interceptors.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "sdk"))

import pytest
from unittest.mock import MagicMock, patch

from culpa.recorder import CulpaRecorder
from culpa.models import LLMCallEvent


class MockMessage:
    def __init__(self, text="Hello!"):
        self.content = [self._TextBlock(text)]
        self.stop_reason = "end_turn"
        self.model = "claude-sonnet-4-6-20251001"
        self.usage = self._Usage()

    class _TextBlock:
        def __init__(self, text):
            self.type = "text"
            self.text = text

    class _Usage:
        input_tokens = 50
        output_tokens = 20
        cache_read_input_tokens = 0
        cache_creation_input_tokens = 0

    def model_dump(self):
        return {"model": self.model, "stop_reason": self.stop_reason}


def test_anthropic_interceptor_records_call():
    """Test that the Anthropic interceptor records LLM calls."""
    recorder = CulpaRecorder()
    recorder.start_session("interceptor test")

    from culpa.interceptors.anthropic import AnthropicInterceptor

    # Create a mock Anthropic client
    mock_response = MockMessage("I fixed the bug!")

    with patch("anthropic.resources.messages.Messages.create", return_value=mock_response):
        interceptor = AnthropicInterceptor(recorder)
        interceptor.install()

        try:
            import anthropic
            client = anthropic.Anthropic(api_key="fake-key")
            response = client.messages.create(
                model="claude-sonnet-4-6-20251001",
                max_tokens=1024,
                messages=[{"role": "user", "content": "Fix the bug"}],
            )
            assert response == mock_response
        finally:
            interceptor.uninstall()

    events = recorder.get_events()
    assert len(events) == 1
    assert isinstance(events[0], LLMCallEvent)
    assert events[0].response_content == "I fixed the bug!"
    assert events[0].token_usage.input_tokens == 50
    assert events[0].token_usage.output_tokens == 20


def test_anthropic_interceptor_uninstall():
    """Test that the interceptor is properly removed on uninstall."""
    import anthropic
    recorder = CulpaRecorder()
    recorder.start_session("test")

    original = anthropic.resources.messages.Messages.create

    from culpa.interceptors.anthropic import AnthropicInterceptor
    interceptor = AnthropicInterceptor(recorder)
    interceptor.install()
    interceptor.uninstall()

    assert anthropic.resources.messages.Messages.create == original


def test_anthropic_interceptor_context_manager():
    """Test using interceptor as context manager."""
    import anthropic
    recorder = CulpaRecorder()
    recorder.start_session("test")

    original = anthropic.resources.messages.Messages.create

    from culpa.interceptors.anthropic import AnthropicInterceptor
    with AnthropicInterceptor(recorder):
        # Inside context, method is patched
        assert anthropic.resources.messages.Messages.create != original

    # Outside context, method is restored
    assert anthropic.resources.messages.Messages.create == original


def test_openai_interceptor_records_call():
    """Test that the OpenAI interceptor records LLM calls."""
    recorder = CulpaRecorder()
    recorder.start_session("openai interceptor test")

    class MockChoice:
        class message:
            content = "OpenAI response"
            tool_calls = None
        finish_reason = "stop"

    class MockOAIResponse:
        choices = [MockChoice()]
        class usage:
            prompt_tokens = 30
            completion_tokens = 15

    try:
        import openai
        from culpa.interceptors.openai import OpenAIInterceptor

        with patch("openai.resources.chat.completions.Completions.create", return_value=MockOAIResponse()):
            interceptor = OpenAIInterceptor(recorder)
            interceptor.install()
            try:
                client = openai.OpenAI(api_key="fake-key")
                client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": "Hello"}],
                )
            finally:
                interceptor.uninstall()

        events = recorder.get_events()
        assert len(events) == 1
        assert isinstance(events[0], LLMCallEvent)
        assert events[0].response_content == "OpenAI response"
    except ImportError:
        pytest.skip("openai not installed")
