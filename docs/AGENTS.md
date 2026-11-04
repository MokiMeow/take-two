# Agents and humans

Two reasoning agents, one deterministic coordinator, and named humans. **Agents propose; humans decide; code checks and releases.**

## Setting up the two agents
- Create **two separate Switch agent identities**, because one identity can hold only one live role.
- Each connects to `#production` and explicitly takes its exclusive role.
- Both are configured to accept messages from the coordinator.
- Before delegating, the coordinator checks that the expected holder is present and inspects `target_statuses`. A missing, unavailable or `not_permitted` target is shown as a failure, never silently skipped.

## Script Supervisor (reasoning agent, role `script-supervisor`)
- **Runs as:** a Claude Code session managed by Switch Console.
- **Gets:** a job (`job_id`, `script_rev`, `constraints_rev`) and the documents, which it loads with `load_internal_documents`.
- **Does:** the scene breakdown at script lock. On a change, it answers "what must this scene keep?": hard rules, preferences, and the story cost of each candidate.
- **Must not:** pick an option, change the schedule, or edit documents.

## 1st AD (reasoning agent, role `first-ad`)
- **Runs as:** a Codex session managed by Switch Console.
- **Gets:** the change, the constraints, and the Supervisor's answer. It is always asked **after** the Supervisor replies.
- **Returns:** 2–3 full manifests: times, setup and wrap, people, location, kit. Option types: change location, reorder scenes, reduce coverage. Moving to another day only if day-2 facts are confirmed.
- **Must not:** mark an option feasible. Only the checker does that.

## Coordinator (custom Switch agent, no LLM)
- **Registered once** with `POST /agents` as a custom connector, using a personal registration key so the user owns it. Its identity is stored and reused.
- **Owns:** every mutable document, the change loop, the checker, question cards, renders, releases and the ledger.
- **Understands only structured commands** (`/change <entity> <id> <field> <value>`). Free-text reports become pending until a human confirms them. No hidden LLM parsing.
- **Publishes explicitly** to Discord rooms. Room links are navigation only and relay nothing.

## Humans
| Role | Decides | Where |
|---|---|---|
| Director | Creative choices | `#production` |
| Producer | Money, location permission | `#production` |
| Client (optional) | Their deliverable, proposed via `#client` | `#client` |
| Crew | Confirm releases, report problems | `#crew`, `#day-<n>` |
| Anyone | Can put a safety hold on a scene | any room |

**Enforcement:** Switch lets anyone the coordinator's addressing policy allows answer a card, and the first answer settles it. So the coordinator stores the authorised answerers per decision and checks `answered_by`. Anyone else's answer releases nothing; a fresh card is posted. We don't claim per-card restriction unless the addressing policy really provides it.

## Rules for both agents (in `agents/*.md`)
- Reply in the exact JSON format, with `job_id`, both revisions, and the coordinator addressed. Anything else is rejected and retried once.
- Say `unknown` rather than guess a fact.
- Stale replies (old revisions) are discarded without comment.
