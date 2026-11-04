# W8: the crew answers through Switch, and every changed duty is confirmed

Same rules as W4–W6 (no edits to Switch, `ui/`, `render/`, `agents/`; LF; files under 500 lines; credentials only in ignored files; Claude commits; real-Switch proof). Writable: `coordinator/`, `scripts/`, `fixtures/`, `templates/`, `pyproject.toml`, `uv.lock`, `docs/UI-CONTRACT.md` (contract section), `work/W8-*`, `data/`.

Background: `work/W7.md` (your critique) and `work/CLAUDE-CRITIQUE.md`. Both agree on the items below. They are in priority order; finish and prove each before starting the next.

## 1. Changed-duty confirmation (fixes the broken promise)
Today "affected" means *earliest call changed* (`coordinator/release.py:63`), so a location change or a kit change needs no confirmation and the UI then claims "Everyone is on release N". Replace it:
- For each person, compute their **duties** in a release: call time, and for each scene they are in: location, start/end, role in scene, and required kit they handle (camera/sound person owns capabilities).
- `acks.expected` = everyone whose duties differ from the duties in the release **they last confirmed** (not merely the previous release). Unchanged people carry forward.
- Add `Release.duty_changes: {person: [short lines]}` to state, e.g. `["Scene 3: rooftop → stairwell", "Call 16:15 (was 16:15)"]` for display and for the crew message.
- Update tests and the W6 day: r2 (rooftop) and r4 (recorder → lav for Leela) must now require confirmations from the people whose duties changed.

## 2. Personal duty cards (crew answer with one tap)
After a release is published, send **each person in `acks.expected`** a native Switch question (single choice) addressed to them, bound to the release id and revisions:
- Prompt: their personal changes ("Release 3 · Maya: Scene 1 moves to 15:40, stairwell. Call 15:25.").
- Options: **Confirm** / **Can't make it** (with optional note via custom text).
- Confirm records the ack exactly like "confirm r3" today. "Can't make it" + note becomes a **pending report** from that person (W5 path), visible in state, and the AD/authority must confirm a structured change; it never changes facts by itself.
- Only that person's answer counts (check sender identity; Switch does not restrict by person, see `E:/DevDrive/switch/core/switch_core/session_activity/service.py:465`). Another person's answer is ignored and the card is replaced once, within expiry (reuse W6's replacement rule).
- A newer release supersedes open cards from older releases (close them as outdated, like decisions). Restart-safe and deduped.
- Keep text "confirm rN" working as a fallback.
Discord renders single-choice buttons (`bridges/collaboration/discord/adapter.py:1455`); Mattermost uses the typed answer form. Prove it on Mattermost; note Discord as untested if the bridge is not configured.

## 3. Free text → proposed change → one-tap confirmation
When a known crew member writes free text that looks like a constraint ("Sorry, I have to leave at 6", "running 20 min late", "recorder battery dead"), turn it into a **proposed structured change** and send the responsible authority (per the W6 authority table) a native card: "Maya says: 'Sorry, I have to leave at 6'. Record `person maya hard_stop 18:00`? · Record · Ignore". Record = exactly the same path as typing `/change` (authority-checked); Ignore leaves it pending/dismissed.
- Extraction: ask the **first-ad** worker role (existing agent, bounded JSON reply `{entity, target, field, value, confidence}`) with the message, the sender's id and the production date/timezone. Validate against the allowed fields list and the known people/locations/capabilities; anything ambiguous or low-confidence stays a pending report with no card. The model never grants authority.
- For the rehearsal harness, the simulated first-ad answers this job too.

## 4. "Since you last confirmed" for each person
Add `CrewMember.since_confirmed: [short lines]`: the differences between their duties in the current release and in the release they last confirmed (empty if up to date). Deterministic, from item 1.

## 5. Judge quickstart
Add `QUICKSTART.md` at the repo root with two honest paths:
- **Replay (no Switch, ~5 min):** Node version, `npm ci --prefix ui`, `npm run dev --prefix ui`, open `http://localhost:5173/?fixtures=day`. Verify it on a clean copy of the repo in `data/` (fresh `npm ci`).
- **Real loop (Switch + Docker, no Discord, no agent subscriptions):** the exact commands to start Switch, prepare credentials, and run `scripts/demo_day.py`, with the expected output. Remove hard-coded `E:` paths in favour of an env var or argument (`scripts/switch/start.ps1:9` and anything else you find), keeping the current machine working.

## Acceptance
- `uv run pytest -q` green with tests for every rule above (wrong person answering a duty card, superseded cards, can't-make-it → pending, extraction rejects unknown names/fields/ambiguous times, since_confirmed against a non-latest baseline).
- `scripts/demo_day.py` re-run twice against real Switch: crew confirm through **duty cards** (simulated people answering the cards), one person answers "Can't make it" once and the AD records the proposed change through the card, and Maya's free-text "I have to leave at 6" becomes a proposed change confirmed by the AD through a card. Re-record `fixtures/ui-state/day/` (overwrite) and keep the original `0N-*.json` untouched.
- Review server on :8787 with the final state; `work/W8-REPORT.md` in the W4 format, including the exact card texts people saw.
