# W6: a shoot day where more than one thing goes wrong

Start only after W5 is merged. Same rules as W4/W5 (no edits to Switch, `ui/`, `render/`, `agents/`; LF; files under 500 lines; credentials only in ignored files; Claude commits).

Writable: `coordinator/`, `scripts/`, `fixtures/`, `templates/`, `pyproject.toml`, `uv.lock`, `docs/UI-CONTRACT.md` (contract section), `work/W6-*`, `data/`.

## Why
The demo shows one change (rooftop refused) and one follow-up (Maya's hard stop). Real shoot days fail in many small ways. The checker already understands availability windows, hard stops, permission windows, daylight (`light_until`), travel time and kit status. Make the full loop handle these as first-class changes, so the demo can show a day where several things go wrong and the crew is never on a stale plan.

## Scenarios (each must run through the real loop: record → hold → delegate → check → decide → release → confirm)
1. **Late actor.** `/change person dev late_by 40` (or `available 15:40`). Every scene Dev is in that now starts before he arrives is held. Options from the AD may reorder scenes (shoot Dev-free work first) or shift times; the checker enforces availability, travel and hard stops. Scene ripple: later scenes move, and only people whose call time changed must re-confirm.
2. **Kit failure.** `/change capability sound_recorder unavailable`. Scenes requiring it are held. Options: a scene that can be shot without sync sound (only if the script supervisor's must_keep allows), or the `second_camera`/`lav` capability if confirmed, or a later slot after a replacement arrives (`available` window on the capability is fine to add if simple).
3. **Losing light.** `/change location park light_until 17:20` (clouds) or `/change location courtyard window 14:00-16:30`. Exterior scenes whose shooting runs past the new limit fail; interiors stay valid.
4. **Overrun.** `/change scene s1 overrun 25` (a take went long). Downstream scenes shift by the overrun plus travel; any that now break a hard stop, window or light limit are held and re-planned. This is a new fact type: add it to constraints and the checker with tests.

Rules:
- Each `/change` is authority-checked like W4 (`late_by`/`available` by the AD, kit by the AD or camera, light/window by the producer, overrun by the AD or script supervisor). Map any name you choose into `docs/UI-CONTRACT.md` and the fields list the UI's report form uses: `location: permission, window, light_until`, `person: hard_stop, available, late_by`, `scene: status, overrun`, `capability: status`.
- Only held scenes are re-planned; valid scenes are never touched unless a ripple forces them, and then the release says "moved" with old → new times.
- A release lists every person whose call time changed; `acks.expected` is exactly those people.

## The day-long rehearsal
Add `scripts/demo_day.py` (same harness as `demo_dry_run.py`, real Switch, simulated people and workers): one shoot day where, in order, (a) the rooftop is refused, (b) Dev is 40 minutes late, (c) the sound recorder dies, (d) Scene 1 overruns by 25 minutes. Each change produces a new release (r2, r3, r4, r5) unless two arrive while a question is open, in which case the question closes as outdated and one release covers both.

After every beat (each change recorded, each hold, each decision opened, each release, all confirmations) write the `/api/state` JSON to `fixtures/ui-state/day/NN-<beat>.json`. These become the dashboard's replay for the video, so they must be real outputs, not hand-written. Keep the existing `fixtures/ui-state/0N-*.json` untouched.

## Acceptance
- `uv run pytest -q` green, with tests for every scenario's checker rule and authority check.
- `scripts/demo_day.py` run twice from a reset against the real Switch with identical normalized results; fixtures written; a review server on :8787 serving the final state.
- `work/W6-REPORT.md` in the W4 format, including for each scenario: what the crew saw in chat (the exact HOLD and release texts).
