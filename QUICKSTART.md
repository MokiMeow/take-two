# Run Take Two

Two ways in. The replay needs only Node. The real loop runs the whole shoot day against your own Switch server.

## 1. Replay the recorded shoot day (about 5 minutes)

Needs **Node 24 LTS** (tested with 24.11.1 and npm 11.6.2). From the repository root:

```bash
npm ci --prefix ui
npm run dev --prefix ui
```

Open **http://localhost:5173/?fixtures=day**. Step through the day with the arrow keys or the Replay control at the top:

| Moments | What happens |
|---|---|
| 1 to 3 | The director approves the first plan; release 1 goes out and is confirmed |
| 4 to 10 | The rooftop refuses, Maya says she must leave at 6, the stale card closes, Arun picks the stairwell, release 2 |
| 11 to 16 | Dev is 40 minutes late; scenes 1 and 2 move together, release 3 |
| 17 to 21 | The sound recorder dies; the confirmed lav mic replaces it, release 4 (only Leela re-confirms) |
| 22 to 26 | Scene 1 runs 25 minutes over; scene 2 slides, release 5, everyone confirmed |

The replay is read-only. It plays back the Control Room snapshots recorded from the real run in [`fixtures/ui-state/day/`](fixtures/ui-state/day); it does not run agents or send messages. Set models are drawn in the browser. Release media (call sheets and preview clips) need the real loop's server below.

## 2. The real loop on your own Switch

Needs Docker Desktop (Linux containers), Node 24 LTS, [uv](https://docs.astral.sh/uv/) and a checkout of [Switch](https://github.com/sandbox-quantum/switch) at commit **989225d8a13f6f36359c54f52d86aec01c4e0826**. No Discord account or agent subscription is needed for this path. A cold Docker build and the renderer's first bundle take longer than five minutes.

From PowerShell in this repository:

```powershell
$env:SWITCH_SOURCE = 'C:/path/to/your/switch'
uv sync --locked
./scripts/switch/start.ps1
uv run python -m scripts.judge_credentials
uv run --env-file data/judge.env python -m scripts.demo_day
uv run --env-file data/judge.env python -m scripts.demo_day
uv run python -m scripts.serve_demo --settings data/w8-demo/settings.json
```

What each step does:

- **`start.ps1`** checks the Switch commit and starts the Switch, Mattermost and gateway containers. It creates local admin credentials only if they are missing, in the ignored `scripts/switch/.env`.
- **`judge_credentials`** signs in to the local gateway and creates (or reuses) a personal registration key, saved only in the ignored `data/judge.env`. It prints no secret values.
- **`demo_day`** registers the coordinator and the two role holders, creates the private production room, and drives all 26 moments through the real Switch server: role-addressed jobs, native question cards and their answers, renders and media uploads. It uses its own ledger in `data/w8-demo/`, backs it up and resets it on each run, and rewrites the replay snapshots. The first run records a baseline; the second compares against it and fails on any difference.
- **`serve_demo`** serves the Control Room and its media on **http://127.0.0.1:8787/**.

The run ends with:

```text
Beat 26: r5-confirmed
{"release": "r5", "beats": 26, "normalized_match": true, "expected": ["maya", "dev", "leela"]}
```

Open **http://127.0.0.1:8787/** for the Control Room and **http://127.0.0.1:8065/** for Mattermost. Ports: Switch 8000, Mattermost 8065, the running rehearsal 8789, the review server 8787. If `ui/dist` is missing, run `npm ci --prefix ui` and `npm run build --prefix ui` first.

In this path the people (test Mattermost accounts) and the two role holders (`scripts/day_workers.py`) are scripted, so the day is repeatable; everything between them is real Switch traffic. Crew members answer their duty cards in Mattermost with Switch's typed card form (for example `A42 q1=1`). To put the crew on Discord and run Claude Code and Codex in the two roles, follow [`docs/SETUP.md`](docs/SETUP.md).

## Tests

```bash
uv run pytest -q                       # 320 tests, Python 3.12
npm run lint --prefix ui
npm run build --prefix ui
```
