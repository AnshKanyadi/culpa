# Using Culpa with Claude Code

Culpa's proxy mode sits between Claude Code and the Anthropic API, transparently recording every LLM call without modifying Claude Code's behavior.

## Setup

```bash
# Terminal 1: Start the proxy
culpa proxy start --name "fixing auth bug" --watch .

# Terminal 2: Point Claude Code at the proxy
ANTHROPIC_BASE_URL=http://localhost:4560 claude
```

That's it. Use Claude Code normally — every LLM call and file change is recorded.

## Stopping

Press `Ctrl+C` in the proxy terminal, or from any terminal:

```bash
culpa proxy stop
```

The session is automatically saved to `~/.culpa/sessions/`. If you've run `culpa login`, it also uploads to the dashboard.

## Background mode

If you don't want the proxy in a separate terminal:

```bash
# Start in background
culpa proxy start --background --name "fixing auth bug" --watch .

# Set env vars for the current shell
eval $(culpa proxy env)

# Run Claude Code
claude

# When done
culpa proxy stop
```

## What gets recorded

- Every LLM call Claude Code makes (model, messages, response, tokens, latency)
- Tool calls (file reads, writes, terminal commands) captured as LLM tool_use events
- File changes on disk (if `--watch` is used)
- Streaming responses are captured in full after the stream completes

## Viewing the session

```bash
# Start the dashboard
culpa serve

# Open http://localhost:8000
# Your session appears in the sessions list with full timeline, event detail, and fork support
```

## Troubleshooting

**Claude Code says "connection refused"**: Make sure the proxy is running (`culpa proxy status`).

**Events show 0 tokens**: Some API errors are still recorded as events. Check the event detail for error information.

**File changes not appearing**: Make sure you passed `--watch .` when starting the proxy.
