"""Tests for the Culpa proxy server."""
from __future__ import annotations

import asyncio
import json
import pytest
import aiohttp
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from culpa.proxy import CulpaProxy, _detect_provider, _get_upstream_url


# ─── Unit tests ───


def test_detect_provider_anthropic():
    assert _detect_provider("/v1/messages") == "anthropic"


def test_detect_provider_openai():
    assert _detect_provider("/v1/chat/completions") == "openai"


def test_detect_provider_unknown():
    assert _detect_provider("/v1/models") == "unknown"


def test_upstream_url_anthropic():
    url = _get_upstream_url("anthropic", "/v1/messages")
    assert url == "https://api.anthropic.com/v1/messages"


def test_upstream_url_openai():
    url = _get_upstream_url("openai", "/v1/chat/completions")
    assert url == "https://api.openai.com/v1/chat/completions"


# ─── Integration tests with mock upstream ───


@pytest.fixture
def mock_anthropic_response():
    return {
        "id": "msg_test",
        "type": "message",
        "model": "claude-sonnet-4-20250514",
        "content": [{"type": "text", "text": "Hello from test!"}],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


@pytest.mark.asyncio
async def test_proxy_records_non_streaming(mock_anthropic_response, unused_tcp_port_factory):
    """Test that the proxy correctly records a non-streaming request."""
    # Set up a mock upstream server
    upstream_port = unused_tcp_port_factory()

    async def mock_handler(request):
        return web.json_response(mock_anthropic_response)

    upstream_app = web.Application()
    upstream_app.router.add_post("/v1/messages", mock_handler)
    upstream_runner = web.AppRunner(upstream_app)
    await upstream_runner.setup()
    upstream_site = web.TCPSite(upstream_runner, "127.0.0.1", upstream_port)
    await upstream_site.start()

    try:
        # Patch the upstream URL
        import culpa.proxy as proxy_mod
        original_base = proxy_mod.ANTHROPIC_API_BASE
        proxy_mod.ANTHROPIC_API_BASE = f"http://127.0.0.1:{upstream_port}"

        # Start proxy
        proxy_port = unused_tcp_port_factory()
        proxy = CulpaProxy(port=proxy_port, session_name="test-proxy")
        await proxy.start()

        try:
            # Send a request through the proxy
            async with aiohttp.ClientSession() as session:
                resp = await session.post(
                    f"http://127.0.0.1:{proxy_port}/v1/messages",
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 100,
                    },
                    headers={"x-api-key": "test-key", "anthropic-version": "2023-06-01"},
                )
                assert resp.status == 200
                body = await resp.json()
                assert body["content"][0]["text"] == "Hello from test!"

            # Verify recording
            assert proxy._request_count == 1
            assert len(proxy.recorder.get_events()) == 1
            event = proxy.recorder.get_events()[0]
            assert event.model == "claude-sonnet-4-20250514"
            assert event.token_usage.input_tokens == 10
            assert event.token_usage.output_tokens == 5
        finally:
            await proxy.stop()
            proxy_mod.ANTHROPIC_API_BASE = original_base
    finally:
        await upstream_runner.cleanup()


@pytest.mark.asyncio
async def test_proxy_records_streaming(unused_tcp_port_factory):
    """Test that the proxy correctly streams and records a streaming request."""
    upstream_port = unused_tcp_port_factory()

    sse_body = (
        b"event: message_start\n"
        b'data: {"message":{"model":"claude-sonnet-4-20250514","usage":{"input_tokens":8}}}\n\n'
        b"event: content_block_start\n"
        b'data: {"content_block":{"type":"text"}}\n\n'
        b"event: content_block_delta\n"
        b'data: {"delta":{"type":"text_delta","text":"Streamed!"}}\n\n'
        b"event: content_block_stop\n"
        b"data: {}\n\n"
        b"event: message_delta\n"
        b'data: {"delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":3}}\n\n'
        b"event: message_stop\n"
        b"data: {}\n\n"
    )

    async def mock_stream_handler(request):
        resp = web.StreamResponse()
        resp.content_type = "text/event-stream"
        await resp.prepare(request)
        # Send in multiple chunks to simulate real streaming
        for i in range(0, len(sse_body), 50):
            await resp.write(sse_body[i:i+50])
            await asyncio.sleep(0.01)
        await resp.write_eof()
        return resp

    upstream_app = web.Application()
    upstream_app.router.add_post("/v1/messages", mock_stream_handler)
    upstream_runner = web.AppRunner(upstream_app)
    await upstream_runner.setup()
    upstream_site = web.TCPSite(upstream_runner, "127.0.0.1", upstream_port)
    await upstream_site.start()

    try:
        import culpa.proxy as proxy_mod
        original_base = proxy_mod.ANTHROPIC_API_BASE
        proxy_mod.ANTHROPIC_API_BASE = f"http://127.0.0.1:{upstream_port}"

        proxy_port = unused_tcp_port_factory()
        proxy = CulpaProxy(port=proxy_port, session_name="test-stream")
        await proxy.start()

        try:
            # Send streaming request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://127.0.0.1:{proxy_port}/v1/messages",
                    json={"model": "claude-sonnet-4-20250514", "messages": [{"role": "user", "content": "Hi"}], "stream": True},
                    headers={"x-api-key": "test-key", "anthropic-version": "2023-06-01"},
                ) as resp:
                    assert resp.status == 200
                    # Read all streamed data
                    body = await resp.read()
                    assert b"Streamed!" in body

            # Verify recording
            assert proxy._request_count == 1
            event = proxy.recorder.get_events()[0]
            assert event.response_content == "Streamed!"
            assert event.token_usage.input_tokens == 8
            assert event.token_usage.output_tokens == 3
        finally:
            await proxy.stop()
            proxy_mod.ANTHROPIC_API_BASE = original_base
    finally:
        await upstream_runner.cleanup()


@pytest.mark.asyncio
async def test_proxy_health_check(unused_tcp_port_factory):
    """Test the proxy health check endpoint."""
    proxy_port = unused_tcp_port_factory()
    proxy = CulpaProxy(port=proxy_port)
    await proxy.start()

    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.get(f"http://127.0.0.1:{proxy_port}/health")
            assert resp.status == 200
            body = await resp.json()
            assert body["status"] == "ok"
            assert body["proxy"] == "culpa"
    finally:
        await proxy.stop()


@pytest.mark.asyncio
async def test_proxy_unknown_path(unused_tcp_port_factory):
    """Test that unknown paths return 404."""
    proxy_port = unused_tcp_port_factory()
    proxy = CulpaProxy(port=proxy_port)
    await proxy.start()

    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.get(f"http://127.0.0.1:{proxy_port}/v1/unknown")
            assert resp.status == 404
    finally:
        await proxy.stop()


@pytest.mark.asyncio
async def test_proxy_saves_session(unused_tcp_port_factory):
    """Test that stopping the proxy saves the session to disk."""
    proxy_port = unused_tcp_port_factory()
    proxy = CulpaProxy(port=proxy_port, session_name="save-test")
    await proxy.start()

    path = await proxy.stop()
    assert path is not None
    assert path.exists()

    data = json.loads(path.read_text())
    assert data["name"] == "save-test"

    # Clean up
    path.unlink(missing_ok=True)
