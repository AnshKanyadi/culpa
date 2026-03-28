"""Tests for SSE chunk parsing — Anthropic and OpenAI streaming formats."""
from __future__ import annotations

from culpa.proxy_parser import (
    AnthropicStreamParser,
    OpenAIStreamParser,
    parse_sse_lines,
    parse_anthropic_stream,
    parse_openai_stream,
)


# ─── SSE line parsing ───


def test_parse_sse_lines_basic():
    raw = b"event: message_start\ndata: {\"type\":\"message_start\"}\n\n"
    events = parse_sse_lines(raw)
    assert len(events) == 1
    assert events[0][0] == "message_start"
    assert '"message_start"' in events[0][1]


def test_parse_sse_lines_multiple_events():
    raw = (
        b"event: message_start\ndata: {\"a\":1}\n\n"
        b"event: content_block_delta\ndata: {\"b\":2}\n\n"
        b"event: message_stop\ndata: {\"c\":3}\n\n"
    )
    events = parse_sse_lines(raw)
    assert len(events) == 3
    assert events[0][0] == "message_start"
    assert events[1][0] == "content_block_delta"
    assert events[2][0] == "message_stop"


def test_parse_sse_lines_openai_format():
    raw = b"data: {\"id\":\"chatcmpl-1\",\"choices\":[{\"delta\":{\"content\":\"Hi\"}}]}\n\ndata: [DONE]\n\n"
    events = parse_sse_lines(raw)
    assert len(events) == 2
    assert events[1][1] == "[DONE]"


# ─── Anthropic stream parser ───


def test_anthropic_parser_basic():
    parser = AnthropicStreamParser()
    parser.feed_event("message_start", {
        "message": {
            "model": "claude-sonnet-4-20250514",
            "usage": {"input_tokens": 50},
        }
    })
    parser.feed_event("content_block_start", {"content_block": {"type": "text"}})
    parser.feed_event("content_block_delta", {"delta": {"type": "text_delta", "text": "Hello "}})
    parser.feed_event("content_block_delta", {"delta": {"type": "text_delta", "text": "world!"}})
    parser.feed_event("content_block_stop", {})
    parser.feed_event("message_delta", {"delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 10}})
    parser.feed_event("message_stop", {})

    result = parser.finish()
    assert result.model == "claude-sonnet-4-20250514"
    assert result.response_content == "Hello world!"
    assert result.input_tokens == 50
    assert result.output_tokens == 10
    assert result.stop_reason == "end_turn"


def test_anthropic_parser_tool_use():
    parser = AnthropicStreamParser()
    parser.feed_event("message_start", {"message": {"model": "claude-sonnet-4-20250514", "usage": {"input_tokens": 20}}})
    parser.feed_event("content_block_start", {
        "content_block": {"type": "tool_use", "id": "tool_1", "name": "read_file"}
    })
    parser.feed_event("content_block_delta", {"delta": {"type": "input_json_delta", "partial_json": '{"path":'}})
    parser.feed_event("content_block_delta", {"delta": {"type": "input_json_delta", "partial_json": '"src/main.py"}'}})
    parser.feed_event("content_block_stop", {})
    parser.feed_event("message_delta", {"delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 5}})

    result = parser.finish()
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "read_file"
    assert result.tool_calls[0]["input"] == {"path": "src/main.py"}
    assert result.stop_reason == "tool_use"


def test_parse_anthropic_stream_from_bytes():
    raw = [
        b'event: message_start\ndata: {"message":{"model":"claude-sonnet-4-20250514","usage":{"input_tokens":10}}}\n\n',
        b'event: content_block_start\ndata: {"content_block":{"type":"text"}}\n\n',
        b'event: content_block_delta\ndata: {"delta":{"type":"text_delta","text":"Hi"}}\n\n',
        b'event: content_block_stop\ndata: {}\n\n',
        b'event: message_delta\ndata: {"delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":1}}\n\n',
        b'event: message_stop\ndata: {}\n\n',
    ]
    result = parse_anthropic_stream(raw)
    assert result.response_content == "Hi"
    assert result.model == "claude-sonnet-4-20250514"
    assert result.input_tokens == 10
    assert result.output_tokens == 1


# ─── OpenAI stream parser ───


def test_openai_parser_basic():
    parser = OpenAIStreamParser()
    parser.feed_chunk({"model": "gpt-4", "choices": [{"delta": {"content": "Hello "}, "finish_reason": None}]})
    parser.feed_chunk({"model": "gpt-4", "choices": [{"delta": {"content": "world!"}, "finish_reason": None}]})
    parser.feed_chunk({"model": "gpt-4", "choices": [{"delta": {}, "finish_reason": "stop"}]})
    parser.feed_chunk({"usage": {"prompt_tokens": 15, "completion_tokens": 5}})

    result = parser.finish()
    assert result.model == "gpt-4"
    assert result.response_content == "Hello world!"
    assert result.input_tokens == 15
    assert result.output_tokens == 5
    assert result.stop_reason == "stop"


def test_openai_parser_tool_calls():
    parser = OpenAIStreamParser()
    parser.feed_chunk({"model": "gpt-4", "choices": [{"delta": {"tool_calls": [{"index": 0, "id": "tc_1", "function": {"name": "get_weather", "arguments": ""}}]}, "finish_reason": None}]})
    parser.feed_chunk({"model": "gpt-4", "choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"city":'}}]}, "finish_reason": None}]})
    parser.feed_chunk({"model": "gpt-4", "choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '"NYC"}'}}]}, "finish_reason": None}]})
    parser.feed_chunk({"model": "gpt-4", "choices": [{"delta": {}, "finish_reason": "tool_calls"}]})

    result = parser.finish()
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "get_weather"
    assert result.tool_calls[0]["input"] == {"city": "NYC"}


def test_parse_openai_stream_from_bytes():
    raw = [
        b'data: {"model":"gpt-4","choices":[{"delta":{"content":"OK"},"finish_reason":null}]}\n\n',
        b'data: {"model":"gpt-4","choices":[{"delta":{},"finish_reason":"stop"}]}\n\n',
        b'data: {"usage":{"prompt_tokens":5,"completion_tokens":1}}\n\n',
        b'data: [DONE]\n\n',
    ]
    result = parse_openai_stream(raw)
    assert result.response_content == "OK"
    assert result.stop_reason == "stop"
    assert result.input_tokens == 5
