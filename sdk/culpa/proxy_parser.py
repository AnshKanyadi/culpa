"""SSE chunk parsing for Anthropic and OpenAI streaming formats."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParsedLLMResponse:
    """Assembled response from streaming chunks."""
    model: str = ""
    response_content: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    stop_reason: Optional[str] = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    raw_chunks: list[dict[str, Any]] = field(default_factory=list)



class AnthropicStreamParser:
    """
    Parses Anthropic SSE streaming chunks.

    Events:
      message_start  → model, usage (input tokens)
      content_block_start → tool_use block info
      content_block_delta → text or tool input chunks
      message_delta  → stop_reason, usage (output tokens)
      message_stop   → stream done
    """

    def __init__(self) -> None:
        self.result = ParsedLLMResponse()
        self._current_block_type: Optional[str] = None
        self._current_tool: Optional[dict] = None
        self._tool_input_json = ""

    def feed_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Process a single SSE event and update the accumulated result."""
        self.result.raw_chunks.append({"event": event_type, "data": data})

        if event_type == "message_start":
            msg = data.get("message", {})
            self.result.model = msg.get("model", "")
            usage = msg.get("usage", {})
            self.result.input_tokens = usage.get("input_tokens", 0)
            self.result.cache_read_tokens = usage.get("cache_read_input_tokens", 0)
            self.result.cache_write_tokens = usage.get("cache_creation_input_tokens", 0)

        elif event_type == "content_block_start":
            block = data.get("content_block", {})
            self._current_block_type = block.get("type")
            if self._current_block_type == "tool_use":
                self._current_tool = {
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": {},
                }
                self._tool_input_json = ""

        elif event_type == "content_block_delta":
            delta = data.get("delta", {})
            delta_type = delta.get("type")
            if delta_type == "text_delta":
                self.result.response_content += delta.get("text", "")
            elif delta_type == "input_json_delta":
                self._tool_input_json += delta.get("partial_json", "")

        elif event_type == "content_block_stop":
            if self._current_block_type == "tool_use" and self._current_tool:
                try:
                    self._current_tool["input"] = json.loads(self._tool_input_json) if self._tool_input_json else {}
                except json.JSONDecodeError:
                    self._current_tool["input"] = {"_raw": self._tool_input_json}
                self.result.tool_calls.append(self._current_tool)
                self._current_tool = None
                self._tool_input_json = ""
            self._current_block_type = None

        elif event_type == "message_delta":
            delta = data.get("delta", {})
            self.result.stop_reason = delta.get("stop_reason")
            usage = data.get("usage", {})
            self.result.output_tokens = usage.get("output_tokens", 0)

    def finish(self) -> ParsedLLMResponse:
        """Return the fully assembled response."""
        return self.result


class OpenAIStreamParser:
    """
    Parses OpenAI SSE streaming chunks.

    Each chunk is `data: {json}\n\n` with choices[0].delta.
    `data: [DONE]` signals the end.
    """

    def __init__(self) -> None:
        self.result = ParsedLLMResponse()
        self._tool_calls_by_index: dict[int, dict] = {}

    def feed_chunk(self, data: dict[str, Any]) -> None:
        """Process a single SSE data chunk and update the accumulated result."""
        self.result.raw_chunks.append(data)

        if not self.result.model and data.get("model"):
            self.result.model = data["model"]

        choices = data.get("choices", [])
        if not choices:
            usage = data.get("usage")
            if usage:
                self.result.input_tokens = usage.get("prompt_tokens", 0)
                self.result.output_tokens = usage.get("completion_tokens", 0)
            return

        choice = choices[0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason")

        if finish_reason:
            self.result.stop_reason = finish_reason

        if delta.get("content"):
            self.result.response_content += delta["content"]

        if delta.get("tool_calls"):
            for tc in delta["tool_calls"]:
                idx = tc.get("index", 0)
                if idx not in self._tool_calls_by_index:
                    self._tool_calls_by_index[idx] = {
                        "id": tc.get("id", ""),
                        "name": tc.get("function", {}).get("name", ""),
                        "arguments": "",
                    }
                if tc.get("function", {}).get("arguments"):
                    self._tool_calls_by_index[idx]["arguments"] += tc["function"]["arguments"]

    def finish(self) -> ParsedLLMResponse:
        """Assemble accumulated tool call fragments and return the complete response."""
        for tc in sorted(self._tool_calls_by_index.values(), key=lambda x: x.get("id", "")):
            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except json.JSONDecodeError:
                args = {"_raw": tc["arguments"]}
            self.result.tool_calls.append({
                "id": tc["id"],
                "name": tc["name"],
                "input": args,
            })
        return self.result



def parse_sse_lines(raw: bytes) -> list[tuple[str, str]]:
    """Parse raw SSE bytes into (event_type, data_string) pairs."""
    events = []
    current_event = ""
    current_data_lines: list[str] = []

    for line in raw.decode("utf-8", errors="replace").split("\n"):
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            current_data_lines.append(line[6:])
        elif line == "" and (current_event or current_data_lines):
            data_str = "\n".join(current_data_lines)
            events.append((current_event or "message", data_str))
            current_event = ""
            current_data_lines = []

    return events


def parse_anthropic_stream(raw_chunks: list[bytes]) -> ParsedLLMResponse:
    """Parse accumulated Anthropic SSE chunks into a complete response."""
    parser = AnthropicStreamParser()
    raw = b"".join(raw_chunks)
    for event_type, data_str in parse_sse_lines(raw):
        if data_str.strip():
            try:
                data = json.loads(data_str)
                parser.feed_event(event_type, data)
            except json.JSONDecodeError:
                pass
    return parser.finish()


def parse_openai_stream(raw_chunks: list[bytes]) -> ParsedLLMResponse:
    """Parse accumulated OpenAI SSE chunks into a complete response."""
    parser = OpenAIStreamParser()
    raw = b"".join(raw_chunks)
    for _, data_str in parse_sse_lines(raw):
        data_str = data_str.strip()
        if data_str == "[DONE]":
            break
        if data_str:
            try:
                data = json.loads(data_str)
                parser.feed_chunk(data)
            except json.JSONDecodeError:
                pass
    return parser.finish()
