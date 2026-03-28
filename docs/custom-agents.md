# Using Culpa with Custom Agents

Any tool or script that talks to the Anthropic or OpenAI API can be recorded through the proxy.

## With environment variables

```bash
# Start the proxy
culpa proxy start --name "testing my agent" --watch .

# Point your script at the proxy
ANTHROPIC_BASE_URL=http://localhost:4560 python my_agent.py
OPENAI_BASE_URL=http://localhost:4560 python my_openai_agent.py
```

The proxy auto-detects the provider from the request path:
- `/v1/messages` → forwarded to `api.anthropic.com`
- `/v1/chat/completions` → forwarded to `api.openai.com`

## With the SDK (alternative)

If you control the agent's source code, you can use the SDK directly instead of the proxy:

```python
import culpa

culpa.init("my session name")

# Your agent code here — all Anthropic/OpenAI calls are intercepted automatically

session = culpa.stop()
```

## When to use proxy vs SDK

| | Proxy | SDK |
|---|---|---|
| No source code access | Yes | No |
| Claude Code / Cursor | Yes | No |
| Custom Python agents | Yes | Yes |
| Non-Python tools | Yes | No |
| File change tracking | `--watch .` | `watch_directory="."` |
| Latency overhead | ~1ms | ~0ms |

## Proxy CLI reference

```bash
culpa proxy start [--port 4560] [--name "session"] [--watch .] [--background]
culpa proxy stop
culpa proxy status
culpa proxy env    # prints export commands, use with: eval $(culpa proxy env)
```
