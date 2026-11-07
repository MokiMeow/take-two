# Architecture

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Collaboration server | **Switch** (pinned commit), run with Docker Compose. Fallback: Switch Console | The hackathon's required platform. Rooms, roles, documents, native questions, chat bridges |
| Production room | **Mattermost** (built into Switch) | Private room where options are argued and the director decides |
| Crew rooms | **Discord** via the Switch bridge | Where crews already talk. Only approved plans arrive here |
| Coordinator | **Python 3.12**: `httpx`, `websockets`, `pydantic`, `sqlite3` | A custom Switch agent (no LLM). Owns the state machine, checks, release ledger |
| Reasoning agents | **Claude Code / Codex sessions run by Switch Console**, one per role | Switch-native agents; they receive work by role and reply with structured proposals |
| Checker | Plain Python inside the coordinator | Deterministic: same input, same verdict. No model opinion |
| Previews | **Remotion 4** (React/TypeScript), one fixed composition, `inputProps` = shot manifest | Renders a 5-second clip of the option's isometric set model from data, not from generated code |
| Call sheet | Remotion `renderStill` to PNG, plus a Markdown text version | The call sheet is made from the same manifest as the preview, so they can't disagree |
| Set models | `ui/src/sets/maquette.ts` on the MIT Anatomy isometric kit | One drawing shared by the Control Room and the rendered previews, so the director and the crew see the same picture |
| Fixtures | YAML: script/brief, constraints, crew list | Small, supplied data for one 3-scene film |

Runtime shape: **one coordinator process, one fixed renderer bundle, two worker identities.** The coordinator calls the Node renderer as a time-limited subprocess, with absolute paths and a manifest file; the same props go to composition selection and rendering. Pin exact package versions and the Switch images, and install the render browser during setup.

Not used: the Switch Tasks protocol (unfinished), emoji reactions as input (not delivered to agents), Switch budgets as a per-room cap (they are per workspace or agent).

## Rooms

```
                 Switch server
  ┌───────────────────────────────────────────────────────┐
  │                                                       │
  │  #production   (Mattermost, private)                  │
  │    Director (human), Producer (human, optional)       │
  │    Script Supervisor agent  ·  1st AD agent           │
  │    Coordinator  (owns documents, questions, releases) │
  │                                                       │
  │        │ explicit publish (links do not relay)        │
  │        ▼                                              │
  │  #crew          (Discord)   standing crew channel     │
  │  #day-<n>       (Discord)   one per shoot day,        │
  │                             created from a template   │
  │    crew members (humans) · Coordinator                │
  └───────────────────────────────────────────────────────┘
```

- **`#production`:** all options, arguments and decisions. The crew never sees unapproved options.
- **`#crew`:** holds and approved releases; crew confirm here.
- **`#day-<n>`:** the coordinator creates one per shoot day with `create_room_from_yaml` (`room.bridge` = the Discord bridge's display name, explicit `channel_type`, coordinator listed under `agents`). Templates create the structure only; the coordinator then creates the day's documents itself with `create_room_document`, because YAML documents belong to the human owner and agents can't update them.
- **Optional `#client`:** for brand or creator shoots, the client proposes changes here; only the director's approved version moves on.

## The change loop

Every change, big or small, follows one loop:

```
 RECORD ──▶ HOLD ──▶ DELEGATE ──▶ CHECK ──▶ DECIDE ──▶ RELEASE ──▶ CONFIRM
   │                                          │
   └──── a newer change arrives anywhere ─────┴──▶ close stale question, restart at CHECK
```

| Step | Who | What happens |
|---|---|---|
| **Record** | Coordinator | Accepts a short structured change command (`/change location rooftop permission refused`: entity, field, value, reporter, source message ID). Free text becomes a pending report that a human confirms. Writes a new constraints revision. Unconfirmed facts are stored as `unknown`, never as true |
| **Hold** | Coordinator | If the change breaks the current plan, posts "Scene 3 on hold, update coming" to the crew within seconds |
| **Delegate** | Coordinator → roles | Role-addressed messages, in order: first `script-supervisor` (what must the scene keep?), then `first-ad` with that answer. Each job has an ID, a deadline and one retry. Replies for old revisions are discarded |
| **Check** | Coordinator | Every candidate gets `pass`, `fail` or `needs_verification`. Only `pass` options can be approved. `needs_verification` asks the responsible human to confirm the fact, which creates a new revision and a re-check. If none pass: "no feasible option, here's why" |
| **Decide** | The named human | A native Switch question tied to `{script_rev, constraints_rev, candidate_ids}`. Options: A, B, or "Neither, here's my note". It expires; silence picks nothing |
| **Release** | Coordinator | Re-checks inputs after every async step and again just before sending. Commits the release and its outbox entries together, renders the call sheet, uploads to Discord with a release ID |
| **Confirm** | Crew | A recognised crew member explicitly confirms *that* release ID (a bare "yes" is ambiguous). Replies to an older one get "That's release 1; the current plan is release 2" |

### One change at a time
Changes and release commits are **serialized per production**. A new change invalidates pending jobs, renders and questions. Decisions are bound to `{request_id, script_rev, constraints_rev, candidate_id, manifest_hash}`. The hash covers the canonical manifest without its own hash field; a preview is reused only if its manifest hash matches the approved candidate. If a change lands while a Discord send is in flight, the coordinator records the order and issues a hold. There is no atomic transaction spanning SQLite and Discord, and we don't pretend there is.

### Two speeds
- **Creative path:** the choice changes what the audience sees, so each option gets a 5-second sketch preview.
- **Fast path:** pure logistics (a call time moves 30 minutes) goes out as text, with no render, and only to the people affected.

### Who decides what
| Decision type | Decides | Others can |
|---|---|---|
| Creative (story, shots, location look) | Director | propose |
| Money (extra cost, overtime) | Producer | propose |
| Location permission | Producer (or the location contact they name) | report |
| Client deliverable | Client, via the director | propose |
| Safety | **Anyone can hold.** Release needs recorded clearance from the named responsible person plus passing hard checks | raise |

Creative approval can never override a refused permission or an open safety hold. Conflicting instructions from two people pause the release; they don't pick a winner. On a small team one person can hold several of these.

**How authority is enforced:** Switch lets anyone allowed by the coordinator's addressing policy answer a question, and the first answer settles it. So each decision stores its authorised answerers, and the coordinator checks `answered_by` against them. An answer from anyone else releases nothing: it is recorded, and a fresh question is issued.

## Release states

Kept separate on purpose:

```
proposed → checked → approved → published → acknowledged (per person)
                                    │
                                    └──▶ superseded (when a newer release is published)
```

"Approved" doesn't mean the crew has it, and "published" doesn't mean they've read it. The AD sees exactly who hasn't confirmed the current release.

**Validity is tracked separately from progress.** A scene becomes unusable the moment it's invalid, even before a replacement exists; unaffected scenes stay valid. Publication is tracked per destination and per file as `pending`, `sent`, `uncertain` or `failed`. A timeout after sending is `uncertain`: reconcile first, and any retry keeps the same release ID (a duplicate post is possible and acceptable).

**Confirmation policy:** every release is a complete snapshot. Only the people affected are asked to confirm again; others' duties are carried forward and shown as "unchanged". The "3 of 3" counter says which policy it uses.

## Data model

### Constraint schema (supplied YAML, versioned as Switch documents)
```yaml
timezone: Asia/Kolkata         # all times are +05:30
people:
  - id: maya
    role: actor
    available: ["2026-11-06T15:00+05:30/2026-11-06T18:00+05:30"]
    hard_stop: "2026-11-06T18:00+05:30"
locations:
  - id: rooftop
    permission: refused        # confirmed | refused | unknown
    permission_authority: producer
    windows: []
    light_until: "2026-11-06T17:55+05:30"   # entered by a human, not calculated
  - id: stairwell
    permission: confirmed
    windows: ["2026-11-06T14:00+05:30/2026-11-06T20:00+05:30"]
travel_min:                    # directed: from -> to
  rooftop->stairwell: 15
capabilities:                  # verified kit, not a full inventory
  gimbal: confirmed
  second_camera: unknown
scenes:
  - id: s3
    hard: ["confession is intelligible and confidential in the story"]
    preferences: ["visually secluded", "sunset"]
```
**Unknown facts can't pass silently.** An option that depends on anything `unknown` gets `needs_verification`, never `pass`.

### Manifest (what every candidate resolves to)
Scene and shot IDs, assigned people, location, start and end, setup and wrap minutes, required capabilities, and the source revisions. The checker validates the manifest, not the agent's prose.

### Candidate (what an agent proposes)
```json
{
  "candidate_id": "s3-stairwell",
  "script_rev": 1, "constraints_rev": 3,
  "changes": [{"scene": "s3", "location": "stairwell", "shots": ["wide", "two-shot"]}],
  "story_cost": "Loses the sunset silhouette; keeps the confession private",
  "manifest_hash": "sha256:..."
}
```

### Ledger (coordinator SQLite, the authority for local decisions)
Tables: `inbox` (with the processed event position), `changes`, `jobs`, `questions` (the exact opening payload), `renders`, `releases`, `publications`, `acks`, `outbox`.
- Outcomes are deduplicated by `(session_id, request_id)`.
- Processing is committed **before** calling Switch's `delivered`.
- On restart: restore the identity, reconcile documents, fetch undelivered outcomes, and resume unfinished effects.

Switch keeps an outcome owed until it is acknowledged, but it doesn't re-send it on a healthy stream, so the coordinator fetches pending outcomes itself after a restart.

## Repo layout

```
take-two/
├── coordinator/          Python: Switch client, state machine, checker, ledger
│   ├── switch_client.py    register (POST /agents), WebSocket, heartbeat, ops, questions
│   ├── loop.py             RECORD → … → CONFIRM state machine
│   ├── checker.py          deterministic constraint checks
│   ├── release.py          manifest → call sheet → publish → acks
│   └── ledger.py           SQLite: changes, questions, releases, acks, outbox
├── render/               Remotion: Preview (5 s) and CallSheet (still) compositions
├── templates/            Switch room YAML: production, crew, shoot-day
├── agents/               Role instructions: script-supervisor.md, first-ad.md
├── fixtures/             The demo film: script, constraints, crew
├── scripts/              setup, reset-demo, smoke test
├── docs/                 this folder
└── .env.example          names only, never values
```
