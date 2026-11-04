# W5: make the live state clean for the crew and the dashboard

You are fixing the coordinator so the live `/api/state` reads like a production office, not like a log. Claude rebuilt the dashboard (ui/, read-only for you) and connected it to your W4 rehearsal server on :8787. These problems are visible there today. Fix them in order. Commit nothing (Claude commits). Keep the W4 rules: no edits to Switch, `ui/`, `render/`, `agents/`; LF line endings; files under 500 lines; credentials only in ignored files; prove everything with tests and one real-Switch rehearsal.

Writable: `coordinator/`, `scripts/`, `fixtures/`, `templates/`, `pyproject.toml`, `uv.lock`, `docs/UI-CONTRACT.md` (contract section only), `work/W5-*`, `data/`.

## 1. Room chatter must not become "reported changes" (blocker)
In the W4 rehearsal state, `changes` holds about 35 entries with `entity: "scene", target: "unconfirmed", field: "report", status: "pending_confirmation"` whose `value` is:
- the coordinator's **own** posts (HOLD notices, releases, "Release r2", stale-reply corrections, option summaries, "Report recorded as pending…", "No Discord bridge yet…"),
- the coordinator's **own** job briefs to `@first-ad` / `@script-supervisor` (JSON),
- room-document notices ("📄 updated room document …"),
- the director's **card answers** (`A20 q1=2, "keep the confession private"`),
- and a real crew message ("Sorry, I have to leave at 6.").

The timeline gets the matching "@switch-agent-…:localhost reported a change; structured confirmation is required." lines (38 of 73 items).

Fix:
- Never treat messages authored by the coordinator's own agent or sender identity as reports. Never treat worker replies, native question answers (the `A<n> …` typed form or any message the question system consumed), or Switch system/document notices as reports.
- A free-text human message is a *possible* report only when it comes from a known crew/authority identity, is not a command, and is not a reply the loop already consumed. Keep at most one pending report per message, and show it in state once, not twice.
- Add tests that replay the W4 rehearsal's own messages and prove none of them becomes a change or a timeline "reported a change" item, while "Sorry, I have to leave at 6." from Maya still becomes one pending report.

## 2. Encoding damage
Room-document notices arrive as `“constraints-r3\udc9d.` (a lone surrogate where the closing quote was). Find where text is decoded (likely bytes split across a chunk or `surrogateescape`) and fix it at the source; never put lone surrogates in state or the ledger. Add a test with multi-byte punctuation split across a frame boundary.

## 3. Names, not ids, in state
The UI must never need to parse Switch ids. Add display fields (additive, keep the old ones):
- `Decision.authority_name` (e.g. "Arun"), `Decision.answer.answered_by_name`.
- `Change.reporter_name`.
- `CrewMember.role_label` ("Actor", "Camera / sound").
- `Release.publications[].room_name` ("#production", "#day-1", "#crew"); never a bare UUID.
- Timeline `text` must use names: "Nila (producer) reported…", never `@switch-…:localhost`.
Names come from trusted config/fixtures (crew.yaml, authority config), never from the message text.

## 4. Times are timestamps
`Change.value` for `person.hard_stop` is `"18:00"`. Keep `value` as typed, and add `Change.at` with the full ISO timestamp (production timezone, production day) for any time-valued field. The checker already resolves this; expose what it used.

## 5. From Claude's review of W4
- `pyproject.toml`: `--basetemp=data/pytest-w4-default` and `cache_dir` fail with access denied on this machine (115 errors from a plain `uv run pytest`). Make a clean checkout run `uv run pytest -q` green with no extra flags, and remove or repair the locked `data/pytest-*` directories you created.
- `loop.py` malformed-reply branch: an unparseable reply without `job_id` burns the newest job's retry even if another worker sent it. Choose the job by the sender's role first.
- `loop.py` `_question`: move the inner `from coordinator.render_props import hhmm` to module level.
- `recovery.py` `finish_catchup`: confirm the 45 s `catchup_deadline` is enforced; if not, time out into a visible error item and keep effects paused.

## 6. Contract
Update `docs/UI-CONTRACT.md` with every field added in W4 (`Candidate.schedule`, `Decision.must_keep`, `Decision.requirements_note`) and W5, and state plainly that `published` means accepted by Switch for relay, not delivered.

## Processes
You may stop the W4 review server (Python PID 51872 and its uv launcher 17428) and your own test servers. Stop nothing else. Docker/Switch is managed by Claude and is already running; if it is not reachable, report it instead of starting it.

## Acceptance
- `uv run pytest -q` green from a clean shell with no flags.
- Re-run `scripts/demo_dry_run.py` twice from a reset against the real Switch; in the resulting `/api/state`: zero changes whose reporter is the coordinator, zero `\udc` characters anywhere, every person/room shown by name, the hard stop has `at`. Save the state JSON as `work/W5-state.json` (redact nothing secret into it; it contains no credentials).
- Leave a review server on :8787 serving the final rehearsal state, as in W4, so Claude can check the dashboard.
- Write `work/W5-REPORT.md` in the W4 format (Done / Runtime facts / Needs the human).
