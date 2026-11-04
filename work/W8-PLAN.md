# W8 execution record

Spec: the W8 brief and the seven required repository documents (read), plus W7 and Claude critique.

Ruling: execute inline in this workspace; no git operations, worktrees, or commits because the user reserves commits for Claude. The supplied W8 design authorizes implementation. QUICKSTART.md is expressly requested despite the general writable-path list.

1. Duty comparison: deterministic call, per-scene location/times/setup/wrap, role and owned kit; baseline is each person's latest explicit confirmation. Add regression tests, run red then green, update crew text. Prove r2 relocation and r4 kit audience before cards.
2. Personal cards: persist exact request, release/revision binding, identity checks, one replacement within original expiry, expiry and supersession, atomic ack/pending report. Keep text fallback. Tests include restart, duplicate and wrong-person outcomes.
3. Reports: bounded first-ad extraction job, strict proposal validation using reviewed entities/fields and production date/timezone, no inferred authority. Persist authority Record/Ignore card; Record reuses handle_change with authenticated answerer. Tests include malformed replies, unknown names/fields, ambiguous time, wrong authority and replay.
4. Expose since_confirmed from the same duty comparator; test non-latest baseline and returning to confirmed duties.
5. Portable setup and QUICKSTART; fresh replay copy under data, real Switch rehearsal twice through duty/proposal cards, overwrite day snapshots only, serve final state on 8787. Record exact card texts and limitations in W8-REPORT.

Shared interfaces: duty comparison feeds release expected/duty_changes, cards and since_confirmed. Cards reuse existing outbox open/close/delivered transports. Extraction reuses bounded worker jobs and existing authority-checked changes.

Review focus: stale outcomes after revision changes; another crew member consumes a card; crash between proposal answer and fact recording; no confirmation baseline; ambiguous model timestamps. Every case requires a regression test.

Task 1: complete ? new duty tests red?green; affected/API/contract regression set: 63 passed, 1 skipped. Legacy snapshots remain unchanged through optional wire fields.
Task 2: complete ? five native card regression tests red?green; cards + W4 + Switch client: 31 passed.
Task 3: implementation complete ? nine extraction/confirmation tests red?green; full-suite check running.
Runtime blocker: Docker named pipe denied by sandbox; no Switch/Mattermost listener. Requested human startup while continuing local work.
Task 4: complete ? non-latest per-person baseline and since_confirmed red?green, then 17 W8 tests passed.
Task 5: real Switch/Mattermost repeat produced r5, 26 beats, normalized_match=true. Final hardened-code repeat in progress. Clean replay npm ci passed; Vite cannot launch because esbuild cannot read a protected parent directory. Exact replay browser verification remains a human step.
Final review: fresh read-only reviewer (code-review skill). Two important findings fixed with red?green tests: whitespace-only notes and partial source-time parsing. Reviewer declined Discord, browser replay and live reproducibility; Discord remains untested, replay blocked, live runs independently checked.
Self-review fixes red?green: unknown availability sentinel, truncated source hiding ambiguity, concurrent malformed worker replies, and dismissed preplan report blocking initial /plan.
Ruling: unsupported explicit source calendar dates/timezones/seconds and time ranges stay pending rather than partially interpreted; this may require AD clarification for otherwise valid prose.
Ruling: preserve old day-beat filenames by moving them to an ignored archive, never delete files; the active replay has exactly 26 current snapshots.
Final verification: uv run pytest -q ? 317 passed, 1 skipped, 1 existing warning. Both hardened-code real runs ? r5, 26 beats, normalized_match=true. Current-code review server on8787; HTTP200/r5/3 confirmed/empty personal differences. Headless Edge live dashboard verified without page errors. Report saved to work/W8-REPORT.md. Replay browser check remains explicitly partial due sandbox permissions.
