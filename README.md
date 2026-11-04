# Take Two

**Shoot plans change. Take Two makes sure everyone is on the same one.**

Take Two is a production room built on [Switch](https://github.com/sandbox-quantum/switch) for small crews and creator teams: short films, YouTube teams, small brand shoots, wedding and event videographers, student films.

When something changes (a location falls through, an actor has to leave early, a client changes the brief), the room:

1. **puts the old plan on hold** straight away, so nobody acts on it;
2. **sends the problem to the right agents by role:** the Script Supervisor (story) and the 1st AD (schedule);
3. **checks every option** against the facts it knows: who is free when, which locations are allowed when, travel, hard stops;
4. **asks the right human to decide,** with short sketch previews for creative choices and plain text for simple logistics;
5. **releases one new plan** to the crew's chat, and tracks who has confirmed *that* version.

> A consequential human decision reaches everyone as one consistent, current plan, and anyone who hasn't seen it is visible.

Built for the **Flip the Switch** hackathon (4–7 Nov 2026), **Track 02: creative workflows**.

## Status
Planning only. Per the event rules, no code is written before **4 Nov 2026, 00:01 IST**.

## Docs
| File | What it covers |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Tech stack, rooms, the change loop, release states, data model, repo layout |
| [docs/AGENTS.md](docs/AGENTS.md) | The two reasoning agents, the coordinator, and the humans who decide |
| [docs/FLOW.md](docs/FLOW.md) | Step-by-step walkthrough of one change, end to end |
| [docs/PLAN.md](docs/PLAN.md) | Day-by-day build plan for 4–7 Nov with an exit test per day |
| [docs/DEMO.md](docs/DEMO.md) | The 2:30 demo video script and the real shoot on 6 Nov |
| [docs/RISKS.md](docs/RISKS.md) | Risks, the day-1 abandonment test, and the fallback |
| [docs/SWITCH-NOTES.md](docs/SWITCH-NOTES.md) | The Switch primitives we rely on, checked against the source |
| [docs/RESEARCH.md](docs/RESEARCH.md) | Evidence that shoot plans really change, and what is not verified |
| [debate/](debate/) | How the idea was chosen: three rounds of Claude vs Sol |

## What Take Two does not do
It doesn't scout locations, carry spare batteries or replace a good AD. It doesn't parse arbitrary screenplays or handle budgets, payroll or permits. Its one job is keeping the human's decision and the crew's plan in sync.
