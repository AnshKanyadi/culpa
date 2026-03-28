# CLAUDE.md — Culpa Project Context

## What Is Culpa

Culpa is a deterministic replay and counterfactual debugging engine for AI agents in production. It captures every LLM call, tool invocation, file change, and terminal command with full fidelity — then lets developers replay failures deterministically and fork at any decision point to test "what if?" scenarios.

**One-liner:** A flight recorder for AI agents. Observability tells you what happened. Culpa tells you why.

**Domain:** culpa.dev
**App URL:** app.culpa.dev
**Docs URL:** docs.culpa.dev
**License:** MIT

## Architecture Overview

Culpa has three layers:

### 1. SDK (`sdk/culpa/`)
Python package that developers install via `pip install culpa`. Contains:

- **`recorder.py`** — Core recording engine. Thread-safe. Creates sessions, records events (LLM calls, tool calls, file changes, terminal commands). Each event gets a ULID, microsecond timestamp, parent event ID, and sequence number.
- **`replay.py`** — Deterministic replay engine. Intercepts LLM calls and returns pre-recorded stub responses instead of calling the real API. Zero API cost. Includes divergence detection.
- **`fork.py`** — Counterfactual fork engine. Replays up to a fork point using recorded data, injects an alternative LLM response, then continues live execution in a sandboxed temp directory.
- **`models.py`** — Pydantic v2 models for all event types: `LLMCallEvent`, `ToolCallEvent`, `FileChangeEvent`, `TerminalCommandEvent`, `Session`, `ForkResult`.
- **`interceptors/`** — Monkey-patches for LLM SDKs:
  - `anthropic.py` — Patches `anthropic.Anthropic.messages.create`
  - `openai.py` — Patches `openai.OpenAI.chat.completions.create`
  - `litellm.py` — Patches `litellm.completion`
- **`watchers/filesystem.py`** — Uses `watchdog` to monitor working directory for file changes. Captures full before/after content and diffs. Links changes to triggering LLM calls via timing.
- **`proxy.py`** — Async HTTP proxy server (aiohttp) that sits between coding agents (Claude Code, Cursor) and LLM APIs. Transparently forwards requests while recording. Handles SSE streaming — forwards chunks immediately while accumulating for recording.
- **`proxy_parser.py`** — SSE chunk parsers for Anthropic and OpenAI streaming formats.
- **`cli.py`** — CLI commands: `culpa record`, `culpa replay`, `culpa sessions`, `culpa upload`, `culpa login`, `culpa serve`, `culpa proxy start/stop/status/env`.
- **`__init__.py`** — Exports `culpa.init()` for zero-config recording. Handles auto-upload via `CULPA_RECORD_OUTPUT` env var for subprocess handoff.

### 2. Server (`server/`)
FastAPI backend with SQLite storage.

- **`main.py`** — App entry point. CORS, static files, startup cleanup.
- **`api/auth.py`** — Register, login, logout, /me, API key CRUD. JWT (httpOnly cookies) + API key auth (Bearer culpa_xxx header).
- **`api/sessions.py`** — Session CRUD, scoped by user_id. Supports `?scope=mine|team|all`.
- **`api/events.py`** — Event queries, filterable by type and time range.
- **`api/forks.py`** — Fork execution endpoint.
- **`api/billing.py`** — Stripe Checkout, webhooks (checkout.completed, subscription.deleted, payment.failed), Customer Portal.
- **`api/teams.py`** — Team CRUD, invites, member management, session visibility.
- **`storage/database.py`** — SQLite init, migrations. Tables: users, api_keys, sessions, events, forks, file_snapshots, teams, team_members, team_invites.
- **`storage/repositories.py`** — Data access for sessions, events, forks.
- **`storage/user_repository.py`** — User and API key data access.
- **`storage/team_repository.py`** — Team, member, invite data access.
- **`services/auth.py`** — bcrypt hashing, JWT encode/decode, API key generation (culpa_ prefix, SHA-256 stored).
- **`services/plans.py`** — Plan limits (free: 3 sessions/7-day retention/5 forks; pro: unlimited/90-day/unlimited). Enforcement checks.
- **`services/email.py`** — Resend integration. Templates: welcome, first session, session expiring, limit reached.
- **`dependencies.py`** — `require_user` FastAPI dependency. Accepts JWT or API key.

### 3. Dashboard (`dashboard/`)
React 18 + TypeScript + Vite + Tailwind CSS.

- **Pages:** `SessionsList`, `SessionDetail`, `SessionCompare`, `Landing`, `Login`, `Register`, `ApiKeys`, `Billing`, `BillingSuccess`, `Team`
- **Components:** `Timeline`, `EventDetail`, `LLMCallDetail`, `FileChangeDetail`, `TerminalDetail`, `SessionOverview`, `ReplayControls`, `ForkModal`, `ForkComparison`, `CommandPalette`, `KeyboardShortcutsHelp`, `Skeleton`, `Logo`
- **Hooks:** `useSession`, `useReplay`, `useFork`
- **Auth:** `AuthContext` provider, JWT in httpOnly cookies, protected routes

## Database Schema

```sql
users (id, email, password_hash, name, plan, stripe_customer_id, stripe_subscription_id, plan_expires_at, email_notifications, created_at, updated_at)
api_keys (id, user_id, key_hash, key_prefix, name, created_at, last_used_at, revoked_at)
sessions (id, user_id, name, metadata_json, started_at, ended_at, status, expires_at, visibility)
events (id, session_id, sequence, type, timestamp, parent_event_id, data_json)
forks (id, session_id, fork_point_event_id, injected_response_json, result_events_json, created_at)
file_snapshots (id, session_id, event_id, file_path, content, operation)
teams (id, name, owner_id, created_at)
team_members (team_id, user_id, role, joined_at)
team_invites (id, team_id, email, invited_by, created_at, accepted_at)
```

## How Recording Works

Two modes:

**SDK mode (Python scripts):**
1. User calls `culpa.init()` or `culpa record -- python script.py`
2. Interceptors monkey-patch `messages.create()` / `chat.completions.create()`
3. When agent makes an LLM call, interceptor captures full request + response + timing
4. File watcher captures any file changes with before/after content
5. Session saved to `~/.culpa/sessions/` and optionally uploaded to server

**Proxy mode (Claude Code / Cursor):**
1. User runs `culpa proxy start`
2. Proxy listens on localhost:4560
3. User sets `ANTHROPIC_BASE_URL=http://localhost:4560`
4. All LLM requests flow through proxy → recorded → forwarded to real API
5. Streaming SSE chunks forwarded immediately (zero latency) while accumulated for recording
6. On stop, session saved and uploaded

The subprocess handoff for `culpa record` works via `CULPA_RECORD_OUTPUT` env var — child process writes session JSON to a handoff file, parent reads it.

## How Replay Works

The replay engine loads a recorded session and replaces live LLM calls with pre-recorded stub responses. The agent code receives the exact same response it got during recording, makes the same decisions, calls the same tools, produces the same output. Zero API cost. Includes divergence detection — if execution path differs from recording, it flags where.

## How Forking Works

User selects an LLM call event and provides an alternative response. The fork engine:
1. Replays up to the fork point using recorded stubs (free)
2. Injects the alternative response at the fork point
3. Continues execution live from there, but in a sandboxed temp directory
4. Returns comparison: original timeline vs forked timeline

## Branding

- **Name:** Culpa (always capitalized)
- **Logo:** Two overlapping chevrons pointing left — back one crimson red, front one white
- **Colors:** Background #0a0a0b, Primary accent #DC2626 (crimson), Secondary #F59E0B (amber for warnings/upgrades)
- **Event colors:** LLM=#3B82F6 (blue), Tool=#8B5CF6 (purple), File=#22C55E (green), Terminal=#F97316 (orange), Error=#DC2626 (red)
- **Fonts:** JetBrains Mono for code/monospace, Inter/DM Sans for body
- **Text logo:** Logo mark + "culpa" in JetBrains Mono Bold
- **API key prefix:** `culpa_`
- **Config directory:** `~/.culpa/`
- **Database file:** `culpa.db`

## Business Model

- **Open-source:** Full SDK, server, and dashboard on GitHub (MIT). Anyone can self-host.
- **Culpa Cloud (paid):** Hosted at app.culpa.dev. Free tier: 3 sessions, 7-day retention. Pro $29/mo: unlimited sessions, 90-day retention, teams.
- **Stripe** handles billing. Webhooks for checkout, cancellation, payment failure.
- **Resend** handles transactional emails.

## Tech Stack

- **SDK:** Python 3.10+, Pydantic v2, watchdog, aiohttp, httpx, click/typer
- **Server:** FastAPI, SQLite, python-jose (JWT), passlib (bcrypt), stripe, resend
- **Dashboard:** React 18, TypeScript, Vite, Tailwind CSS, React Query, React Router, sonner (toasts), lucide-react (icons)
- **Proxy:** aiohttp async server

## Environment Variables

```
JWT_SECRET=                    # Required for auth
STRIPE_SECRET_KEY=sk_test_...  # Stripe billing
STRIPE_WEBHOOK_SECRET=whsec_.. # Stripe webhook verification
STRIPE_PRICE_ID=price_...      # Pro plan price ID
RESEND_API_KEY=re_...          # Email sending
FROM_EMAIL=noreply@culpa.dev   # Email sender address
DATABASE_URL=sqlite:///./culpa.db
CORS_ORIGINS=http://localhost:5173,https://app.culpa.dev
ANTHROPIC_API_KEY=             # For testing agent recordings
```

## Running Locally

```bash
# Install SDK
pip install -e ".[server,dev]"

# Start server
python3 -m uvicorn server.main:app --reload

# Start dashboard
cd dashboard && npm install && npm run dev

# Seed demo data
python3 examples/demo_session.py --upload

# Record a test session
culpa record "test" -- python3 test_agent.py

# Start proxy for Claude Code
culpa proxy start --name "session" --watch .
```

## Test Suite

```bash
python3 -m pytest tests/ -v
```

91 tests covering: recorder, replay, fork, interceptors, proxy, proxy parser, auth, plans, billing, teams, emails.

## Known Issues / Active Bugs

- Auto-upload from SDK doesn't work reliably — sessions record locally but don't auto-upload to server even with API key configured
- Fork Pydantic validation error — Session model expects `session_id` but data has `id` (field name mismatch)
- Profile dropdown in dashboard header needs to be clickable with navigation to settings/billing/team
- Timezone display in `culpa sessions` CLI shows raw UTC instead of local time
- API key revoke uses browser `confirm()` instead of inline styled confirmation
- Password validation needs stronger requirements (uppercase, lowercase, number)
- Email validation accepts invalid formats like "user@domain" without TLD

## Code Style

- Python: type hints on all functions, docstrings on all public methods, Pydantic v2 models
- TypeScript: strict mode, proper typing (no `any` unless unavoidable)
- All API responses use Pydantic response models
- Database queries MUST filter by user_id — users must never see each other's data
- Never store plaintext passwords or full API keys
- Use structured logging (not print statements)
- Dark theme everywhere — use Tailwind config color namespace

## Project Structure

```
culpa/
├── sdk/culpa/              # Python SDK
│   ├── __init__.py         # culpa.init(), culpa.stop()
│   ├── recorder.py         # Core recording engine
│   ├── replay.py           # Deterministic replay
│   ├── fork.py             # Counterfactual forking
│   ├── models.py           # Pydantic event models
│   ├── cli.py              # CLI commands
│   ├── proxy.py            # HTTP proxy server
│   ├── proxy_parser.py     # SSE streaming parsers
│   ├── interceptors/       # LLM SDK monkey-patches
│   └── watchers/           # File system watcher
├── server/                 # FastAPI backend
│   ├── main.py
│   ├── api/                # REST routes
│   ├── storage/            # SQLite + repositories
│   ├── services/           # Auth, plans, email
│   └── dependencies.py     # Auth middleware
├── dashboard/              # React frontend
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── hooks/
│       ├── api/
│       └── lib/
├── examples/               # Demo session, usage examples
├── tests/                  # 91 tests
├── docs/                   # Setup guides
├── pyproject.toml          # Python package config
└── CLAUDE.md               # This file
```
