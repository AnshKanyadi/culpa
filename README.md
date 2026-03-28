<p align="center">
  <img src="dashboard/public/culpa-logo.svg" alt="Culpa" width="64" height="64" />
</p>

<h1 align="center">Culpa</h1>

<p align="center">
  Deterministic replay and counterfactual debugging for AI coding agents.
</p>

---

Culpa is a flight recorder for AI agents. It captures every LLM call, tool invocation, file change, and terminal command with full fidelity — then lets you replay the exact failure path or fork at any decision point to run "what if?" experiments.

Works with Claude Code, Cursor, OpenAI-based agents, or anything that talks to the Anthropic/OpenAI API.

## Quick start

### Option 1: Setup script

```bash
git clone https://github.com/AnshKanyadi/culpa
cd culpa
./setup.sh
./start.sh
```

### Option 2: Docker

```bash
git clone https://github.com/AnshKanyadi/culpa
cd culpa
docker compose up
```

Dashboard at `http://localhost:8000`.

### Option 3: Manual

```bash
git clone https://github.com/AnshKanyadi/culpa
cd culpa

python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[all,dev]"

cd dashboard && npm install && npm run dev &
cd server && uvicorn main:app --reload
```

## Recording sessions

### SDK (for your own scripts)

```python
import culpa

culpa.init("Fix authentication bug")

# your agent runs here — all LLM calls are captured

session = culpa.stop()
```

Or from the CLI:

```bash
culpa record "Fix auth bug" -- python my_agent.py
```

### Proxy mode (for Claude Code, Cursor, etc.)

For tools where you can't inject `culpa.init()` into the source code, use the transparent proxy:

```bash
# Terminal 1: start the proxy
culpa proxy start --name "debugging auth" --watch .

# Terminal 2: point your tool at the proxy
ANTHROPIC_BASE_URL=http://localhost:4560 claude
```

The proxy sits between your AI tool and the real API, recording everything transparently. Zero latency added — chunks stream through immediately.

```bash
# When done
culpa proxy stop
```

### Viewing sessions

Open the dashboard to explore recorded sessions:

```bash
culpa serve
# http://localhost:8000
```

The dashboard shows the full event timeline, lets you inspect each LLM call's request/response, view file diffs, and replay or fork the session.

## Replaying

Re-execute a recorded session using the captured LLM responses as stubs. Deterministic, zero API calls, identical behavior every time.

```python
from culpa import CulpaReplayer

replayer = CulpaReplayer(session)
for event in replayer.replay(speed=2.0):
    print(event.description)
```

Or from the CLI:

```bash
culpa replay <session_id>
culpa replay <session_id> --speed 5
```

## Forking

Pick any LLM call in a session, inject a different response, and see what would have happened downstream.

```python
from culpa import CulpaForker

forker = CulpaForker(session)
result = forker.fork_at(
    event_id="01HN...",
    new_response="Keep using bcrypt, just fix the encoding."
)
print(result.divergence_summary)
```

In the dashboard, click the fork icon on any LLM call in the timeline to do this visually.

## Architecture

```
culpa/
├── sdk/culpa/            Python SDK (pip install culpa)
│   ├── recorder.py       Core recording engine
│   ├── replay.py         Deterministic replay
│   ├── fork.py           Counterfactual forking
│   ├── proxy.py          Transparent HTTP proxy for Claude Code/Cursor
│   ├── proxy_parser.py   SSE stream parsing (Anthropic + OpenAI)
│   ├── models.py         Pydantic event models
│   ├── cli.py            CLI (record, replay, proxy, serve)
│   ├── interceptors/     LLM SDK monkey-patches
│   └── watchers/         File system monitoring
├── server/               FastAPI + SQLite backend
│   ├── api/              REST endpoints (sessions, events, forks, auth)
│   ├── storage/          SQLite persistence + repositories
│   └── services/         Auth, plans, email
├── dashboard/            React + TypeScript + Tailwind
│   └── src/
│       ├── pages/        Sessions list, detail, compare, settings
│       └── components/   Timeline, event inspector, fork modal
└── tests/                pytest suite (91 tests)
```

Recording works by monkey-patching LLM SDK clients (or proxying HTTP requests in proxy mode). The filesystem watcher captures before/after content for every file change. Sessions are stored as event streams in SQLite. The fork engine replays deterministically up to the fork point, injects the alternative response, then simulates downstream execution.

## CLI reference

```bash
culpa record "name" -- command        Record a session
culpa sessions                        List recorded sessions
culpa replay <id> [--speed N]         Replay in terminal
culpa upload <id>                     Upload to server
culpa serve [--port 8000]             Start server + dashboard
culpa login                           Authenticate with server
culpa proxy start [--port 4560]       Start recording proxy
culpa proxy stop                      Stop proxy and save session
culpa proxy status                    Check proxy status
culpa proxy env                       Print env vars for proxy
```

## Self-hosting

Culpa is designed to run fully self-hosted with zero external dependencies. The server needs only Python and SQLite. No Stripe, no Resend, no cloud accounts required.

Optional integrations (for the cloud-hosted version):
- **Stripe** — billing for paid plans
- **Resend** — transactional emails
- Both degrade gracefully when not configured

## Stack

- **SDK:** Python 3.12+, Pydantic v2, Typer, aiohttp, Watchdog
- **Server:** FastAPI, SQLite (WAL mode), Uvicorn
- **Dashboard:** React 18, TypeScript, Tailwind CSS, React Query, Zustand

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
