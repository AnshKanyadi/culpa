# Prismo

Prismo is a flight recorder for AI coding agents. It captures every LLM call, tool invocation, file change, and terminal command your agent makes — then lets you replay the exact session deterministically or fork at any decision point to run counterfactual experiments.

---

## Why this exists

AI coding agents are remarkably useful right now, but debugging them is a mess.

When Claude Code or Cursor breaks something — edits the wrong file, misreads a test failure, makes an incorrect assumption that cascades into three more wrong decisions — you can't reproduce it. Run the same task again and you get completely different behavior. The chain of reasoning that caused the failure is gone.

Tools like Langfuse and Braintrust will show you a trace of what happened. That's useful. But a trace doesn't let you *replay* the failure to understand it, and it definitely doesn't let you go back to the moment the agent went wrong, inject a different response, and see what would have happened instead.

Prismo tries to solve both of those problems.

---

## How it works

Three things:

**Record.** Wrap your agent with `prismo.init()` and it transparently intercepts all Anthropic/OpenAI SDK calls, watches the filesystem, and logs terminal commands. No changes to your agent code required.

**Replay.** Re-execute the recorded session using the captured LLM responses as stubs. Deterministic, no API calls, identical behavior every time. Useful for understanding exactly what happened, and for running regression tests against past failures.

**Fork.** Pick any LLM call in the timeline, inject a different response, and simulate what the downstream execution would have looked like. This is the interesting one — it's how you answer "what if the agent had diagnosed the problem correctly at step 3?"

---

## Quick start

```bash
pip install prismo
```

```python
import prismo

prismo.init("Fix authentication bug")

# ... your agent runs here, everything gets captured ...

session = prismo.stop()
```

Or wrap an existing script from the CLI:

```bash
prismo record "Fix auth bug" -- python my_agent.py
```

To explore the recorded session in the dashboard:

```bash
prismo serve
# opens at http://localhost:5173
```

---

## Demo

There's a demo script that simulates a realistic failure worth running:

```bash
python examples/demo_session.py --upload
prismo serve
```

The scenario: an agent is asked to fix a failing authentication test. It reads the test, decides the issue is a bcrypt compatibility problem, and refactors the password hashing to use argon2-cffi. The tests pass. But the agent just locked out 12,847 production users whose existing bcrypt hashes are now unverifiable.

The dashboard shows the full 18-event decision chain, the exact moment the agent misread the situation, and lets you fork at that step with a corrected diagnosis to see where the execution would have diverged.

---

## SDK

```python
import prismo

# zero-config init
prismo.init("Session name")
# ... agent runs ...
session = prismo.stop()

# context manager
with prismo.record("Session name") as recorder:
    # ... agent runs, session ends automatically ...
    pass

# manual recording if you need more control
from prismo import PrismoRecorder

recorder = PrismoRecorder()
recorder.start_session("name")
recorder.record_llm_call(
    model="claude-sonnet-4-6-20251001",
    messages=[...],
    response_content="..."
)
recorder.record_file_change("src/auth.py", "modify", before="old code", after="new code")
recorder.record_terminal_command("pytest", stdout="3 passed", exit_code=0)
session = recorder.end_session()
```

Replay:

```python
from prismo import PrismoReplayer

replayer = PrismoReplayer(session)
for event in replayer.replay(speed=2.0):
    print(event.description)
```

Fork at a decision point:

```python
from prismo import PrismoForker

forker = PrismoForker(session)
result = forker.fork_at(
    event_id="01HN...",
    new_response="I'll keep using bcrypt, just fix the encoding issue."
)
print(result.divergence_summary)
```

---

## CLI

```bash
prismo record "Task description" -- python my_agent.py
prismo sessions                        # list recorded sessions
prismo replay <session_id>             # play back in terminal
prismo replay <session_id> --speed 5   # 5x speed
prismo upload <session_id>             # push to dashboard
prismo serve                           # start server + dashboard
prismo serve --port 8080
```

---

## Architecture

```
prismo/
├── sdk/prismo/          Python SDK
│   ├── recorder.py      Core recording engine
│   ├── replay.py        Deterministic replay
│   ├── fork.py          Counterfactual forking
│   ├── models.py        Pydantic event models
│   ├── cli.py           CLI
│   ├── interceptors/    LLM client monkey-patches (Anthropic, OpenAI, LiteLLM)
│   └── watchers/
│       └── filesystem.py   Watchdog-based file monitoring
├── server/              FastAPI + SQLite backend
└── dashboard/           React + TypeScript + Tailwind UI
    └── src/
        ├── pages/       Sessions list, session detail
        └── components/  Timeline, event inspector, fork modal
```

The recording works by monkey-patching the LLM SDK clients at init time. The filesystem watcher captures before/after content for every file change, which is what makes deterministic replay possible — the replayer doesn't need access to your live filesystem, just the recorded snapshots.

Sessions are stored as event streams. The fork engine replays deterministically up to the fork point, injects the alternative response, then simulates the downstream execution. SQLite with WAL mode handles concurrent read-heavy workloads without a separate database server.

---

## Development setup

```bash
git clone https://github.com/anshkumar/prismo
cd prismo

# install SDK in dev mode
pip install -e ".[all,dev]"

# run tests
pytest tests/ -v

# start the API server
cd server && uvicorn main:app --reload

# start the dashboard (separate terminal)
cd dashboard && npm install && npm run dev
```

---

## Stack

- **SDK:** Python 3.12+, Pydantic v2, Typer, Watchdog
- **Server:** FastAPI, SQLite, Uvicorn
- **Dashboard:** React 18, TypeScript, Tailwind CSS, React Query, Zustand, Framer Motion

---

## Status

Early alpha. Core recording, replay, and forking work. The dashboard is functional. Rough edges exist, particularly around the fork simulation for complex multi-tool sessions. PRs welcome.

---

MIT License
