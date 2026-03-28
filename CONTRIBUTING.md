# Contributing to Culpa

## Dev environment setup

```bash
git clone https://github.com/AnshKanyadi/culpa
cd culpa

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all,dev]"

cd dashboard && npm install && cd ..
```

## Running tests

```bash
python3 -m pytest tests/ -v
```

All tests must pass before submitting a PR. Tests run against an in-memory SQLite database — no external services needed.

## Project structure

- `sdk/culpa/` — Python SDK (recorder, replayer, forker, proxy, CLI)
- `server/` — FastAPI backend (auth, sessions, billing, teams)
- `dashboard/` — React + TypeScript frontend
- `tests/` — pytest suite

## Code style

- Python: formatted with ruff, type hints everywhere, Pydantic models for data
- TypeScript: functional components, Tailwind for styling, React Query for server state
- No unnecessary comments — code should be self-explanatory. Only comment genuinely non-obvious logic.
- No boilerplate docstrings — every docstring should tell you something you can't figure out from the function signature alone.

## Running the dev servers

```bash
./start.sh
```

Or manually:

```bash
source .venv/bin/activate
cd server && uvicorn main:app --reload &
cd dashboard && npm run dev
```

## Submitting a PR

1. Create a branch from `main`
2. Make your changes
3. Run `python3 -m pytest tests/ -v` — all tests must pass
4. Open a PR with a clear description of what changed and why

Keep PRs focused. One feature or fix per PR. If you're making a big change, open an issue first to discuss the approach.

## Architecture notes

- Sessions are stored as event streams in SQLite
- Recording uses monkey-patching on LLM SDK clients (or HTTP proxying for tools like Claude Code)
- The fork engine replays deterministically up to the fork point, then injects the alternative response
- The dashboard is a standard React SPA that talks to the FastAPI backend
- Auth uses JWT cookies for the dashboard, Bearer API keys for SDK uploads
