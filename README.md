# Take Two

**Shoot plans change all day. Take Two keeps the whole crew on one current, checked plan.**

Take Two is a production room built on [Switch](https://github.com/sandbox-quantum/switch) for small film crews and creator teams. When something changes on a shoot day (a location is refused, an actor is late, the sound recorder dies, a scene runs over), it holds what is affected, asks two AI agents for new plans, checks every plan against the facts in code, lets the director choose in Switch, and releases one new versioned plan that each affected crew member confirms.

Built for **Flip the Switch** (4–7 Nov 2026), **Track 02: Personal or Creative Workflow**.

![How Take Two works](docs/explainer/how-it-works.png)

## How Switch is used
Take Two cannot run without Switch. Every person, agent and message goes through it:

| Switch feature | What Take Two does with it |
|---|---|
| **Custom agent registration** (`POST /agents`, WebSocket connection) | The coordinator is a registered Switch agent with its own identity; it reads the rooms and posts holds, releases and corrections. |
| **Rooms + bridges** | The `#production` room (Mattermost) holds the producer, AD and director with the agents. The crew rooms (`#crew`, `#day-1`) live on Discord through Switch's Discord bridge. |
| **Sender identity** | Every message carries its sender's account. The coordinator's authority table decides who may change what (only the producer can change a location permission; only the director's answer counts). |
| **Exclusive agent roles** (`assume_role`) | Two separate agent identities hold the `script-supervisor` and `first-ad` roles; jobs are addressed to the role. |
| **Native question cards** (session approvals) | The director chooses between checked plans on a Switch question card. A card asked on old facts is closed as outdated. |
| **Room documents** | `script-r1` and `constraints-rN` are versioned room documents the agents read. |
| **Media uploads** | Each option's set-model clip and each release's call sheet are uploaded to the room through Switch. |

## Agents connected
| Agent | Runs as | Job |
|---|---|---|
| **Script supervisor** | Claude Code, managed by Switch Console | Says what each scene must keep for the story ("the confession stays private"). |
| **First AD** | Codex, managed by Switch Console | Drafts up to three concrete plans: location, time, cast, shots, kit. |
| **Coordinator** | Python (this repo), registered as a Switch custom agent | Records changes, holds scenes, sends jobs, runs the checker, opens the decision, releases, tracks confirmations. No LLM. |

The agents only propose. A deterministic checker (`coordinator/checker.py`) tests permissions and windows, daylight, hard stops, availability, cast, kit and travel; a plan that fails never reaches the director. A person always decides.

## How the rooms are set up
- `#production` (Mattermost, from the Switch local server): producer, AD, director, both agents and the coordinator.
- `#crew` and `#day-1` (Discord, through the Switch Discord bridge): the cast and crew.
- Step-by-step setup (Discord bot, Console agents): [docs/SETUP-HUMAN.md](docs/SETUP-HUMAN.md). Agent instructions: [agents/](agents/).

## Run it
See **[QUICKSTART.md](QUICKSTART.md)** for both paths:
1. **Replay a recorded shoot day** (Node only, about 5 minutes): the dashboard replays 23 real snapshots of a day where four things go wrong.
2. **The real loop on your own Switch** (Docker + Switch, no Discord or agent subscriptions needed): `scripts/demo_day.py` runs the day against the real Switch server with simulated people and workers.

Tests: `uv run pytest -q` (Python 3.12).

## What happens in the demo day
| Change | Who reports it | Result |
|---|---|---|
| Rooftop permission refused | Producer | Scene 3 held, re-planned to the stairwell; release 2 |
| Dev is 40 minutes late | AD | Scenes 1–2 held, one plan moves both; release 3 |
| Sound recorder dies | AD / camera | All scenes held; plan uses the confirmed lav mic; release 4 |
| Scene 1 runs 25 minutes over | AD / script supervisor | Scene 2 slides; release 5 |

Each release is versioned and fingerprinted; a reply about an old release is caught and corrected in chat.

## Repo map
| Path | What it is |
|---|---|
| `coordinator/` | The Switch agent: loop, checker, ledger, releases, Switch client (Python, FastAPI) |
| `ui/` | The Control Room dashboard (React, Vite); set models drawn with the Anatomy kit |
| `render/` | Remotion renderer for set-model preview clips and call sheets |
| `agents/` | Role instructions for the two Console agents |
| `scripts/` | Real-Switch rehearsals (`demo_day.py`, `demo_dry_run.py`), reset and seed tools |
| `fixtures/` | The film, its facts and the recorded dashboard snapshots |
| `docs/` | Architecture, flow, agents, setup, the explainer |

## Honest limits
- The recorded day uses **simulated people and simulated agents** talking through the real Switch server. Real Console agents and the Discord bridge are set up separately ([docs/SETUP-HUMAN.md](docs/SETUP-HUMAN.md)).
- "Published" means Switch accepted the message for relay, not that a crew member's phone showed it.
- Set models show where people and the camera are, not what the shot will look like.
- Take Two doesn't scout locations, handle budgets or permits, or parse arbitrary screenplays.

## Credits and licences
Switch is Apache 2.0 with a modified Commons Clause (see `coordinator/SWITCH-LICENSE.txt`). The schedule board adapts Subframe's MIT "schedule ripple"; set models use the MIT Anatomy kit (`ui/src/sets/kit/LICENSE`).
