# Using Culpa with Cursor

Culpa's proxy records every LLM call Cursor makes, giving you a complete session you can replay and fork.

## Setup

```bash
# Start the proxy
culpa proxy start --name "refactoring payment module" --watch .
```

Then point Cursor at the proxy. Two options:

**Option A: Environment variable** (recommended)

```bash
ANTHROPIC_BASE_URL=http://localhost:4560 cursor
```

**Option B: Cursor settings**

1. Open Cursor Settings
2. Go to Models → Override API URL
3. Set to `http://localhost:4560`

## Recording

Use Cursor normally. Every AI interaction — edits, chat, inline completions — gets recorded through the proxy.

## Stopping

```bash
culpa proxy stop
```

Or `Ctrl+C` in the proxy terminal. The session saves automatically.

## Viewing

```bash
culpa serve
# Open http://localhost:8000
```

The session shows up with the full timeline of LLM calls, including which model was used, what was asked, what was returned, token counts, and latency.
