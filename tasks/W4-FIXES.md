# W4: fix round for the coordinator

Two independent reviews of W1's coordinator found blockers. Read both in full first: `work/CLAUDE-REVIEW-W1.md` (C1–C7) and `work/W3-REVIEW.md` (F1–F20). Read `render/README.md` and `render/src/schema.ts`: the renderer is real now. Claude is fixing the renderer side at the same time (strict prop validation, held scene rows, limits); its updated schema will be in `render/src/schema.ts` and `work/RENDER-CONTRACT.md` within the hour. Re-read them before writing `render_props.py`.

**Writable:** `coordinator/`, `scripts/`, `templates/`, `fixtures/`, `pyproject.toml`, `uv.lock`, `work/W4-REPORT.md`, `work/W4-PROGRESS.md`, `data/`. Don't edit `ui/`, `render/`, `agents/` or `docs/`; propose changes in the report. The coordinator at 127.0.0.1:8787 (PID 28140) was started by W1. You may stop exactly that PID and restart your own. The Switch server at :8000 is Claude's; use it over HTTP only.

## Fix now, in this order (the demo story in docs/FLOW.md must run end to end)
1. **Worker reply parsing:** F1 / C7. A bounded mention-and-fence extractor, with tests on realistic messages. `agents/*.md` tells workers to reply with one fenced json block addressed to `@take-two-coordinator`.
2. **Render props + manifest identity:** F2 / C1 / C2 / F14 / F17 / F19.
   - `coordinator/render_props.py`, built from an immutable complete release envelope and trusted metadata (script titles, crew names, scene numbers).
   - Hash the manifest, not the props.
   - Capture the CLI's `render-error:` line.
   - Align the limits with the renderer.
   - Test against a pydantic mirror of the zod schemas.
3. **Initial plan → release 1, and the shoot-day room:** F4.
   - A complete three-scene schedule, approved once by the director, commits r1.
   - Provision `#day-1` from `templates/shoot-day.yaml` when a Discord bridge exists. If none exists, show a visible "no Discord bridge yet" state; never crash.
   - Add the missing verified `courtyard->rooftop` travel fact.
   - Give the demo a scripted way to seed the initial plan, `scripts/seed_initial_plan.py`. It goes through the real loop: the AD proposes, the checker passes, the director approves in Mattermost.
3b. **Coordinator-originated jobs need no human command:** the initial planning job is requested by a structured command from an authenticated authority (`/plan day-1`), not by the browser.
4. **Scope:** F5 / F16. Maya's 18:00 hard stop must not hold Scene 2 (it ends 15:35). Re-check actual invalidity per scene. Unresolved scenes persist across a newer change. Replacing a scene frees its old commitments.
5. **Trusted requirements:** F6. Required cast and capabilities per scene come from the script and the reviewed breakdown, not from the worker's manifest. The Supervisor's `must_keep` is stored with the decision and shown on the card. It isn't machine-checked prose, so say so honestly.
6. **The decision card carries the previews:** F7. Upload both preview MP4s and a short checked summary to `production` before opening the card (`POST /agents/{id}/rooms/{room}/media`), then open the card that references them.
7. **Crew text, day label, reset:** C3 / C4 / C5 / C6. Use the exact message formats in C3.
8. **Reconnect barrier:** F3. Pause effects on transport loss, and catch up before applying outcomes or dispatching.
9. **Late outcomes:** F8. A timely answer recorded by the server but delivered after the local expiry is honoured if its revisions are still current.
10. **Honest publication status:** F10. Rename nothing in the contract; document that `sent` means "accepted by Switch for relay". Add a `/api/state` timeline line when a bridge delivery error is observed.
11. **Browser reports:** F15. The Control Room can report and hold conservatively, but can't confirm facts, clear holds or authorize anything.

## Later (don't do now; list in your report if you see cheap wins)
F9 manual uncertain resolution, F11 media-reply correlation, F12 beyond a visible failure line, F13 full projection refactor, F18, F20 cleanup.

## Acceptance
- `uv run pytest` green, with new tests for each item above. Name them in the report.
- `scripts/demo_dry_run.py` drives the whole FLOW story against the **real Switch server** with **simulated workers and a simulated director**, both posting through Switch as separate registered test identities, never by calling loop methods directly. It ends with release 2 published to the production room (Discord not yet connected), Dev's stale reply corrected, and his confirmation counted. Print the final `/api/state` summary.
- Run it twice from a reset ledger with identical results.
- Report as in the worker standard, plus a table: finding ID → fixed / deferred, with file:line and test name.
