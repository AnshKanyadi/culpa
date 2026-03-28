"""
Culpa Proxy — transparent HTTP proxy for recording LLM calls from Claude Code, Cursor, etc.

Sits between the AI tool and the real LLM API, recording every request/response
into a Culpa session while forwarding everything unchanged.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import time
from pathlib import Path
from typing import Any, Optional

import aiohttp
from aiohttp import web

from .recorder import CulpaRecorder
from .utils.serialization import serialize

logger = logging.getLogger(__name__)

ANTHROPIC_API_BASE = "https://api.anthropic.com"
OPENAI_API_BASE = "https://api.openai.com"

PID_FILE = Path.home() / ".culpa" / "proxy.pid"
SESSION_FILE = Path.home() / ".culpa" / "proxy_session.json"


def _detect_provider(path: str) -> str:
    """Detect LLM provider from request path."""
    if "/v1/messages" in path:
        return "anthropic"
    if "/v1/chat/completions" in path:
        return "openai"
    return "unknown"


def _get_upstream_url(provider: str, path: str) -> str:
    """Map a provider name and request path to the upstream API URL."""
    if provider == "anthropic":
        return f"{ANTHROPIC_API_BASE}{path}"
    elif provider == "openai":
        return f"{OPENAI_API_BASE}{path}"
    return ""


def _forward_headers(request: web.Request, provider: str) -> dict[str, str]:
    """Build headers to forward to upstream, removing hop-by-hop headers."""
    skip = {"host", "transfer-encoding", "connection", "keep-alive"}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in skip}
    return headers


class CulpaProxy:
    """Async HTTP proxy server that records LLM calls."""

    def __init__(
        self,
        port: int = 4560,
        session_name: str = "culpa-proxy",
        watch_dir: Optional[str] = None,
    ) -> None:
        self.port = port
        self.session_name = session_name
        self.watch_dir = watch_dir
        self.recorder = CulpaRecorder()
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._watcher: Any = None
        self._request_count = 0

    async def _handle_request(self, request: web.Request) -> web.StreamResponse:
        """Main request handler — detect provider, forward, record."""
        path = request.path
        provider = _detect_provider(path)

        if provider == "unknown":
            if path == "/health":
                return web.json_response({
                    "status": "ok",
                    "proxy": "culpa",
                    "session": self.recorder.session_id,
                    "requests_recorded": self._request_count,
                })
            return web.json_response(
                {"error": f"Unknown path: {path}. Culpa proxy handles /v1/messages and /v1/chat/completions"},
                status=404,
            )

        upstream_url = _get_upstream_url(provider, path)
        headers = _forward_headers(request, provider)
        body = await request.read()

        try:
            parsed_body = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed_body = {}

        is_streaming = parsed_body.get("stream", False)
        model = parsed_body.get("model", "unknown")
        messages = parsed_body.get("messages", [])
        start_time = time.time()

        try:
            if is_streaming:
                return await self._handle_streaming(
                    request, upstream_url, headers, body, parsed_body, provider, model, messages, start_time
                )
            else:
                return await self._handle_non_streaming(
                    upstream_url, headers, body, parsed_body, provider, model, messages, start_time
                )
        except aiohttp.ClientError as e:
            logger.error(f"Upstream connection error: {e}")
            return web.json_response(
                {"error": f"Could not reach {provider} API: {e}", "type": "proxy_error"},
                status=502,
            )

    async def _handle_non_streaming(
        self,
        upstream_url: str,
        headers: dict,
        body: bytes,
        parsed_body: dict,
        provider: str,
        model: str,
        messages: list,
        start_time: float,
    ) -> web.Response:
        """Forward non-streaming request, record, return response."""
        async with aiohttp.ClientSession() as session:
            async with session.post(upstream_url, data=body, headers=headers) as resp:
                resp_body = await resp.read()
                resp_headers = {k: v for k, v in resp.headers.items()
                                if k.lower() not in ("transfer-encoding", "connection")}
                latency_ms = (time.time() - start_time) * 1000

                try:
                    resp_json = json.loads(resp_body)
                    self._record_call(provider, parsed_body, resp_json, latency_ms)
                except Exception as e:
                    logger.warning(f"Failed to record non-streaming response: {e}")

                return web.Response(body=resp_body, status=resp.status, headers=resp_headers)

    async def _handle_streaming(
        self,
        request: web.Request,
        upstream_url: str,
        headers: dict,
        body: bytes,
        parsed_body: dict,
        provider: str,
        model: str,
        messages: list,
        start_time: float,
    ) -> web.StreamResponse:
        """Forward streaming request chunk-by-chunk, accumulate for recording."""
        response = web.StreamResponse()
        accumulated_chunks: list[bytes] = []

        async with aiohttp.ClientSession() as session:
            async with session.post(upstream_url, data=body, headers=headers) as resp:
                response.set_status(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection", "content-length"):
                        response.headers[k] = v
                response.headers["Transfer-Encoding"] = "chunked"

                await response.prepare(request)

                async for chunk in resp.content.iter_any():
                    accumulated_chunks.append(chunk)
                    await response.write(chunk)

                await response.write_eof()

        latency_ms = (time.time() - start_time) * 1000
        try:
            self._record_streaming_call(provider, parsed_body, accumulated_chunks, latency_ms)
        except Exception as e:
            logger.warning(f"Failed to record streaming response: {e}")

        return response

    def _record_call(
        self, provider: str, request_body: dict, response_json: dict, latency_ms: float
    ) -> None:
        """Record a non-streaming LLM call."""
        self._request_count += 1

        if provider == "anthropic":
            content = ""
            for block in response_json.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")
            usage = response_json.get("usage", {})
            self.recorder.record_llm_call(
                model=response_json.get("model", request_body.get("model", "")),
                messages=request_body.get("messages", []),
                response_content=content,
                token_usage={"input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0)},
                latency_ms=latency_ms,
                stop_reason=response_json.get("stop_reason"),
                system_prompt=request_body.get("system"),
            )
        elif provider == "openai":
            choices = response_json.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
            usage = response_json.get("usage", {})
            self.recorder.record_llm_call(
                model=response_json.get("model", request_body.get("model", "")),
                messages=request_body.get("messages", []),
                response_content=content,
                token_usage={"input_tokens": usage.get("prompt_tokens", 0), "output_tokens": usage.get("completion_tokens", 0)},
                latency_ms=latency_ms,
                stop_reason=choices[0].get("finish_reason") if choices else None,
            )

        events = self.recorder.get_events()
        if events:
            last = events[-1]
            logger.info(
                f"[CULPA] Recorded: {request_body.get('model', '?')} "
                f"({last.token_usage.input_tokens} in, "
                f"{last.token_usage.output_tokens} out, "
                f"{latency_ms / 1000:.1f}s)"
            )

    def _record_streaming_call(
        self, provider: str, request_body: dict, chunks: list[bytes], latency_ms: float
    ) -> None:
        """Record a streaming LLM call from accumulated SSE chunks."""
        self._request_count += 1

        if provider == "anthropic":
            from .proxy_parser import parse_anthropic_stream
            parsed = parse_anthropic_stream(chunks)
        elif provider == "openai":
            from .proxy_parser import parse_openai_stream
            parsed = parse_openai_stream(chunks)
        else:
            return

        self.recorder.record_llm_call(
            model=parsed.model or request_body.get("model", ""),
            messages=request_body.get("messages", []),
            response_content=parsed.response_content,
            token_usage={"input_tokens": parsed.input_tokens, "output_tokens": parsed.output_tokens},
            latency_ms=latency_ms,
            stop_reason=parsed.stop_reason,
            system_prompt=request_body.get("system"),
        )

        logger.info(
            f"[CULPA] Recorded (stream): {parsed.model or request_body.get('model', '?')} "
            f"({parsed.input_tokens} in, {parsed.output_tokens} out, {latency_ms / 1000:.1f}s)"
        )

    def _save_session(self) -> Optional[Path]:
        """End the recording session, save to disk, and upload if configured."""
        if self.recorder._session is None:
            return None

        session = self.recorder.end_session()
        sessions_dir = Path.home() / ".culpa" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        path = sessions_dir / f"{session.session_id}.json"
        session_json = serialize(session.model_dump())
        path.write_text(session_json)

        self._try_upload(session_json, session.session_id)

        return path

    def _try_upload(self, session_json: str, session_id: str) -> bool:
        """Attempt to upload the session to the server."""
        import json as _json
        config_path = Path.home() / ".culpa" / "config.json"
        api_key = os.environ.get("CULPA_API_KEY")
        server_url = os.environ.get("CULPA_SERVER_URL")

        if config_path.exists() and (not api_key or not server_url):
            try:
                config = _json.loads(config_path.read_text())
                api_key = api_key or config.get("api_key")
                server_url = server_url or config.get("server_url")
            except Exception:
                pass

        if not api_key:
            return False

        server_url = server_url or "http://localhost:8000"
        try:
            import httpx
            response = httpx.post(
                f"{server_url}/api/sessions",
                content=session_json,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            logger.info(f"Session {session_id} uploaded to {server_url}")
            return True
        except Exception as e:
            logger.warning(f"Auto-upload failed: {e}")
            return False

    async def start(self) -> None:
        """Start the proxy server."""
        self.recorder.start_session(self.session_name, metadata={
            "mode": "proxy",
            "port": self.port,
            "watch_dir": self.watch_dir,
        })

        if self.watch_dir:
            try:
                from .watchers.filesystem import FileSystemWatcher
                self._watcher = FileSystemWatcher(self.watch_dir, self.recorder)
                self._watcher.start()
                logger.info(f"File watcher started on {self.watch_dir}")
            except Exception as e:
                logger.warning(f"Could not start file watcher: {e}")

        self._app = web.Application()
        self._app.router.add_route("*", "/{path_info:.*}", self._handle_request)

        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", self.port)
        await site.start()

        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(json.dumps({
            "pid": os.getpid(),
            "port": self.port,
            "session_id": self.recorder.session_id,
            "session_name": self.session_name,
        }))

        logger.info(f"Culpa proxy listening on http://127.0.0.1:{self.port}")
        logger.info(f"Session: {self.recorder.session_id}")

    async def stop(self) -> Optional[Path]:
        """Stop the proxy and save the session."""
        if self._watcher:
            try:
                self._watcher.stop()
            except Exception:
                pass

        if self._runner:
            await self._runner.cleanup()

        path = self._save_session()

        PID_FILE.unlink(missing_ok=True)

        return path


def run_proxy(
    port: int = 4560,
    session_name: str = "culpa-proxy",
    watch_dir: Optional[str] = None,
) -> None:
    """Run the proxy server (blocking, handles signals for graceful shutdown)."""
    proxy = CulpaProxy(port=port, session_name=session_name, watch_dir=watch_dir)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    saved_path: Optional[Path] = None

    async def run():
        nonlocal saved_path
        await proxy.start()
        stop_event = asyncio.Event()

        def handle_signal():
            stop_event.set()

        loop.add_signal_handler(signal.SIGINT, handle_signal)
        loop.add_signal_handler(signal.SIGTERM, handle_signal)

        await stop_event.wait()

        logger.info("Shutting down proxy...")
        saved_path = await proxy.stop()

    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        saved_path = loop.run_until_complete(proxy.stop())
    finally:
        loop.close()

    if saved_path:
        print(f"\nSession saved: {saved_path}")
        print(f"Events recorded: {proxy._request_count} LLM calls")
