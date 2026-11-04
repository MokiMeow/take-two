# Try Take Two

Take Two keeps a film crew on the approved plan when a location, person or piece of kit changes. Choose a recorded replay or the real Switch integration rehearsal below.

## Replay — no Switch, about five minutes

Use **Node 24 LTS** (verified install: 24.11.1, npm 11.6.2). From the repository root:

```powershell
node --version
npm ci --prefix ui
npm run dev --prefix ui
```

Open **http://localhost:5173/?fixtures=day** in Edge. Use Next moment to step through the recorded shoot day: initial approval, rooftop hold, Maya's proposed hard stop, crew cards, late actor, lav replacement and overrun. The replay is read-only and labelled Replay. It uses recorded HTTP snapshots; it does not run agents, send questions or prove a new decision. Set models are drawn locally. Rendered media URLs need the real-loop review server below.

Fresh-copy check: `npm ci` succeeded in `data/w8-clean-replay` with no inherited node_modules. In the restricted Codex Windows sandbox, launching Vite failed because esbuild could not read a parent directory. Run the three commands in a normal terminal; a successful browser replay on that fresh copy remains a human verification step. No UI source was changed for this workaround.

## Real loop — Switch + Docker, no Discord or agent subscriptions

Prerequisites: Docker Desktop with Linux containers running, Node 24 LTS/npm, [uv](https://docs.astral.sh/uv/), and a Switch source checkout at **989225d8a13f6f36359c54f52d86aec01c4e0826**. Obtain that checkout separately. This repository never edits it. A cold Docker build and renderer download can take considerably longer than five minutes.

From normal PowerShell in this repository:

```powershell
$env:SWITCH_SOURCE = 'C:/path/to/your/switch'
uv sync --locked
./scripts/switch/start.ps1
uv run python -m scripts.judge_credentials
uv run --env-file data/judge.env python -m scripts.demo_day
uv run --env-file data/judge.env python -m scripts.demo_day
uv run python -m scripts.serve_demo --settings data/w8-demo/settings.json
```

`start.ps1` checks the source pin and starts the local Switch/Mattermost/gateway containers. It generates local credentials only when absent in ignored `scripts/switch/.env`. The source path is cached in ignored `data/switch-source.txt`, so this machine's existing checkout continues to work without a tracked drive-specific path.

`judge_credentials` signs in to the local gateway with those generated admin credentials and creates/reuses a **personal registration key**, saved only in ignored `data/judge.env`. It prints no credential values. No external account or provider subscription is needed. Keep both environment files private.

`demo_day` registers simulated worker identities and separate simulated Mattermost people, then drives **real** Switch role messages, native question answers, renders and uploads. It creates/reuses private **w8-production**, backs up and resets only its isolated `data/w8-demo/ledger.sqlite`, and overwrites the day replay snapshots. Files with obsolete day-beat names are moved to `data/w8-demo/fixture-archive`, never deleted; the original top-level `0N-*.json` examples stay untouched. Stop a prior W8 review server with Ctrl+C before rerunning the rehearsal so two coordinators do not share its identity/database.

Expected output ends with:

```text
Beat 26: r5-confirmed
{"release": "r5", "beats": 26, "normalized_match": true, "expected": ["maya", "dev", "leela"]}
```

The first successful run reports `normalized_match: false` because it establishes the baseline. The next reports `true`; disagreement fails the command. Thirteen answered personal/proposal cards are recorded in `data/w8-demo/cards.json`. The release audiences are r1/r2/r3/r5: Maya, Dev, Leela; r4: Leela. Maya's “I have to leave at 6” and Dev's “Can't make it — Running 40 min late” both require the named human AD's Record card before changing facts.

Open **http://127.0.0.1:8787/** for the final Control Room and **http://127.0.0.1:8065/** for Mattermost. The review server serves an existing `ui/dist` build when available; `/api/state` and `/media/…` work independently of that build. To build the Control Room on a fresh machine, run `npm ci --prefix ui` and `npm run build --prefix ui` before starting the review server, or keep the Vite dev server running and open **http://localhost:5173/** without the replay query.

Switch listens on **8000**, Mattermost on **8065**, the running rehearsal API on **8789**, and the final review API on **8787**. Crew answers use Mattermost's native typed card form (for example `A42 q1=1`); Discord buttons are source-supported and **untested** here because no Discord bridge is configured. This rehearsal proves coordinator/transport behavior with simulated people and workers, not real model reasoning or Discord delivery.
