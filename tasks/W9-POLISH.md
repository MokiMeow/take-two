# W9: resolve reports, human card text, one flaky test

Same rules as W4–W8 (no edits to Switch, `ui/`, `render/`, `agents/`; LF; files under 500 lines; Claude commits; real-Switch proof). Writable: `coordinator/`, `scripts/`, `fixtures/`, `pyproject.toml`, `uv.lock`, `docs/UI-CONTRACT.md` (contract section), `work/W9-*`, `data/`. Keep it small and finish today.

## 1. Reports must resolve (bug)
In the W8 day, Maya's "I have to leave at 6" and Dev's "Running 40 min late" stay `status: "pending_confirmation"` in `changes` for the rest of the day, even after the AD recorded the proposed change through the card (`fixtures/ui-state/day/07-maya-change-confirmed.json` onward). The dashboard therefore shows them as still waiting.
- When a proposal card is answered **Record**, mark the source report resolved and link it: add `Change.resolution: "recorded" | "ignored" | "superseded" | null` and `Change.resolved_by_change` (id of the recorded change) and `resolved_at`. **Ignore** → `ignored`. A report that never got a proposal stays pending until someone records or dismisses it.
- A "Can't make it" answer that the authority later records the same way resolves too.
- Status semantics stay as they are for recorded facts; only reports gain a resolution. Document in `docs/UI-CONTRACT.md`.

## 2. Human wording on cards and in `duty_changes` / `since_confirmed`
Today's lines: `Scene 1: kit sound_recorder → lav`, `actor; kit none`, `camera_sound`, `Call 14:45 (was 14:45)`, `Call 15:25 (was unconfirmed)`.
- Use display names everywhere a person reads it: roles from `role_label` ("Camera / sound"), kit from a small trusted label map in fixtures ("sound recorder", "lav mic", "gimbal", "second camera"), locations title-cased.
- Never print an unchanged value as a change: drop `Call 14:45 (was 14:45)`. For a first release write `Call 15:25` (no "(was unconfirmed)").
- Omit empty parts (`kit none`).
- Keep the meaning identical; tests assert the new strings.

## 3. Flaky test
`coordinator/tests/test_w5_boundaries.py::test_catchup_outcome_fetch_cannot_overrun_deadline` failed once in a full-suite run under load and passes alone. Make it deterministic (inject a clock / fake timer instead of wall time).

## Acceptance
- `uv run pytest -q` green twice in a row.
- Re-run `scripts/demo_day.py` once against real Switch; re-record `fixtures/ui-state/day/` (overwrite) so reports show their resolution and the new wording; keep the top-level `0N-*.json` untouched.
- Review server on :8787; `work/W9-REPORT.md` (short, W4 format) with before/after examples of the card texts.
