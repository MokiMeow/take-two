# W1: Switch running + coordinator day-1 slice

**Goal:** by the end of this task, a real Switch server runs locally, and the Python coordinator can do the day-1 thin path on it, as far as possible without the user's Discord token.

**Writable paths:** `coordinator/`, `templates/`, `fixtures/`, `scripts/`, `pyproject.toml`, `uv.lock`, `.env` (create it; never print it), `work/W1-REPORT.md`, `data/`, `out/`. Read-only everywhere else, including `ui/`, `render/` and `docs/` (propose doc changes in the report instead).

## Part A: Switch server (do this first, report blockers immediately in `work/W1-PROGRESS.md`)
1. Docker Desktop is already running (Claude started it). If `docker ps` fails, report it as a blocker; do not try to start Docker yourself.
2. Run Switch with its standalone Docker Compose (`E:\DevDrive\switch\deploy\local\standalone-docker-compose.yml`), following the repo's own docs for env vars. Pin to the checked-out commit. Put any compose overrides or env files in `scripts/switch/`, never inside `E:\DevDrive\switch`.
3. Confirm `/health` and readiness. Find out how to get a **personal registration key** for the local user and how the built-in Mattermost is reached (URL, first login). Write the exact steps into the report.
4. If Docker fails, try Switch Console (`switch-console-x64.exe` from the latest release) and note issue #1335. Don't spend more than 90 minutes on Part A before writing a clear blocker report.

## Part B: coordinator (Python 3.12, `coordinator/`)
Build these modules, each with unit tests (`pytest`, under `coordinator/tests/`):
- `config.py`: loads `.env` (pydantic-settings).
- `switch_client.py`: register with `POST /agents` (custom connector) once and persist the identity to `data/identity.json`; WebSocket connection with ping/pong; stop on `taken_over`; resume from the persisted event position; ops calls with `X-Switch-Connection-Id`; `create_room_document`/`update`; role-addressed messages with `target_roles` and `target_statuses` handling; question cards (`kind: questions`, persisted logical `session_id`, `request_id` per cycle, expiry, `allow_custom_answer`), outcome fetch, `delivered`, `close`; media upload `POST /agents/{id}/rooms/{room_id}/media`; `create_room_from_yaml`.
- `ledger.py`: SQLite schema from ARCHITECTURE "Ledger": inbox with event position, changes, jobs, questions (exact payload), renders, releases, publications, acks, outbox. Atomic commits. Dedupe outcomes by `(session_id, request_id)`.
- `constraints.py` + `checker.py`: the schema in ARCHITECTURE (timezone, availability, hard stops, permission + authority, windows, directed travel, setup/wrap, capabilities, `unknown`). Returns `pass` / `fail` / `needs_verification` with plain-English reasons. **This must be thoroughly tested**: at least 25 cases, including every scenario in `docs/FLOW.md`.
- `commands.py`: parse `/change <entity> <target> <field> <value>`; free text → pending report.
- `loop.py`: the state machine RECORD → HOLD → DELEGATE (Supervisor then AD) → CHECK → DECIDE → RELEASE → CONFIRM, serialized per production, with invalidation of pending jobs, renders and questions on a new change; authority check on `answered_by`; stale-reply correction for crew messages that mention an old release.
- `render_bridge.py`: calls the renderer as a bounded subprocess: `node render/cli.mjs --kind preview|callsheet --manifest <abs json> --out <abs path>` (Claude builds `render/`; until it exists, write a stub that produces a placeholder file and mark it clearly).
- `api.py`: FastAPI + uvicorn on `127.0.0.1:8787`, exactly as in `docs/UI-CONTRACT.md` (state, SSE, changes, media with path-traversal protection, static `ui/dist`).
- `__main__.py`: `uv run python -m coordinator` starts everything.

Also:
- `fixtures/film/`: the demo film from `docs/FLOW.md` (script, constraints r1, crew) as YAML.
- `fixtures/ui-state/*.json`: valid `State` snapshots for six moments: `01-normal`, `02-hold`, `03-two-options`, `04-outdated`, `05-released`, `06-stale-reply`. Claude builds the UI against these, so **write these first** (within your first hour) and make them realistic and consistent with FLOW.md.
- `templates/production.yaml`, `templates/crew.yaml`, `templates/shoot-day.yaml`: Switch room templates (Mattermost production; Discord crew and shoot-day once a Discord bridge exists).
- `agents/` is NOT yours. Claude and the user write the role instructions (dictated with Wispr Flow).

## Acceptance
1. `docker ps` shows Switch running; `/health` OK; the steps to log into Mattermost are in the report.
2. `uv run pytest` is green; the checker has 25+ cases.
3. The coordinator registers on the real server, holds a live connection for 5 minutes with no drop, creates a document in a production room, and opens a real question card visible in Mattermost. Paste the redacted request/response shapes into the report.
4. `GET /api/state` returns a contract-valid `State` built from the ledger; `/api/events` streams an update when you POST a change.
5. Fixtures for the six UI moments exist and validate against a pydantic model of the contract.
6. The report lists exactly what is still needed from the user (Discord bot, Console agents) as numbered steps.

Save the report to `work/W1-REPORT.md` and also give it as your final message. Update `work/W1-PROGRESS.md` every hour with one line per milestone.
