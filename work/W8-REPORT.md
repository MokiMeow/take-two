# W8 report

## 1. Done

W8 changed-duty confirmation, personal native questions, proposed-change confirmation, and personal since-confirmed differences are implemented. Two final-code real Switch/Mattermost rehearsals both finished at r5 with 26 beats and `normalized_match: true` (`work/W8-final-real-1.log`, `work/W8-final-real-2.log`). The fresh replay install passed; launching the exact Vite command is blocked by this sandbox and is explicitly not claimed as verified.

`uv run pytest -q`: **317 passed, 1 skipped, 1 warning** (`work/W8-final-tests.log`). The skip is the existing Windows symlink privilege check; the warning is the existing Starlette/AnyIO deprecation. The full suite includes 31 W8 regressions. The preceding 30-test focused run also passed (`work/W8-focused-final.log`), and the added preplan-report regression passed red?green. Python stays pinned to 3.12 in `pyproject.toml`.

| Acceptance item | Implementation | Evidence |
|---|---|---|
| Full personal duties and each person's last explicit baseline | `coordinator/duties.py:7`, `:23`, `:56`; `coordinator/release.py:64` | `test_location_same_call_needs_all_scene_people`, `test_kit_change_only_sound_owner_needs_confirmation`, `test_since_confirmed_uses_personal_nonlatest_baseline`; real audiences r2 everyone, r4 Leela |
| Immutable release changes and live personal outstanding differences | `coordinator/ui_models.py:178`, `:189`; `coordinator/loop.py:77`; `coordinator/cards.py:141` | Non-latest-baseline test follows Maya from r1 through missed r2 to r3; after her explicit ack the differences empty. Baseline IDs persist independently of capped UI release history. |
| Native personal Confirm / Can't make it, sender check, one replacement, expiry, supersession, text fallback | `coordinator/cards.py:17`, `:77`, `:116`, `:128`; `coordinator/release.py:135` | `test_personal_confirm_and_duplicate_after_restart`, `test_wrong_person_replaced_only_once_with_same_expiry`, `test_cannot_make_it_note_is_pending_and_never_changes_facts`, `test_superseded_cards_and_revision_stale_answers_do_nothing`, `test_expiry_never_confirms_and_text_fallback_closes_card` |
| Crash after card send retries the exact immutable request; answered requests stay answered | `coordinator/dispatcher.py:307`; `coordinator/loop.py:310` | `test_uncertain_card_open_retries_exact_request_after_restart`; duplicate-outcome/restart tests. Uncertain preview uploads remain excluded from automatic retries. |
| Free text ? bounded first-ad extraction ? named authority Record / Ignore | `coordinator/reports.py:19`, `:39`, `:118`, `:133`, `:166`; shared `/change` body `coordinator/changes.py:10`; ingress `coordinator/runtime.py:382` | `test_report_record_card_uses_authority_change_path_once_across_restart`, `test_ignore_and_wrong_authority_never_record`, parameterized unknown/low-confidence/ambiguous rejection tests, stale-proposal test. Actual Maya and Dev cards in the real rehearsal. |
| Bad model JSON/schema, unknown availability, concurrent jobs and long text fail safely | `coordinator/loop.py:187`; `coordinator/reports.py:118` | `test_bad_extraction_schema_retries_once_then_visible_failure`, `test_unknown_availability_cannot_crash_time_extraction`, `test_truncated_source_cannot_hide_ambiguity_and_open_proposal`, `test_bad_json_with_multiple_worker_jobs_gets_bounded_visible_retries` |
| Portable source path, private judge credential preparation, honest quickstart | `scripts/switch/start.ps1:1`, `:16`; `scripts/switch/prepare.py:16`; `scripts/switch/compose.override.yml:7`; `scripts/judge_credentials.py:37`; `QUICKSTART.md:1` | `uv run python scripts/switch/prepare.py`, `uv run python -m scripts.judge_credentials`; no tracked E-drive paths remain in scripts. Current checkout is cached in ignored `data/switch-source.txt`. |
| Real rehearsal, day snapshots, final review server | `scripts/demo_day.py:62`, `:163`, `:173`, `:255`; `scripts/day_workers.py:55`; `scripts/demo_switch.py:136` | Two final-code runs: r5, 26 beats, normalized_match=true in both final-real logs. Day snapshots are real `/api/state` responses. Original top-level six snapshots match the initial clean copy byte-for-byte. |
| Clean replay | `QUICKSTART.md:5`; clean copy `data/w8-clean-replay` | Node **24.11.1**, npm **11.6.2**, fresh `npm ci --prefix data/w8-clean-replay/ui` installed 184 packages successfully. Exact Vite launch failed with esbuild parent-directory access denied. A normal-shell replay remains unverified; this acceptance item is partial. |

All changed source files use LF and remain below 500 lines. No git command, Switch/UI/render/agents edit, global software install, secret output, or deletion of someone else's file was performed. Old day-beat filenames were moved into ignored `data/w8-demo/fixture-archive/`; the active day directory contains exactly 26 snapshots. Local dependencies and clean copies are confined to `data/`.

### Exact native personal card prompts

Duty options are **Confirm / Can't make it**, with optional custom text. Proposal options are **Record / Ignore**. The following are the exact prompts from the successful real run; the same prompts are verified by the normalized repeat. The two unconfirmed r2 cards are included separately below. The 13 answered-card receipts are in ignored `data/w8-demo/cards.json`.

1. **duty ? maya ? option 1** ? Release 1 · Maya: Scene 2: courtyard, 15:25–15:35; actor; kit none; Scene 3: rooftop, 16:45–18:15; actor; kit none; Call 15:25 (was unconfirmed).

2. **duty ? dev ? option 1** ? Release 1 · Dev: Scene 1: stairwell, 15:00–15:15; actor; kit none; Scene 2: courtyard, 15:25–15:35; actor; kit none; Scene 3: rooftop, 16:45–18:15; actor; kit none; Call 14:45 (was unconfirmed).

3. **duty ? leela ? option 1** ? Release 1 · Leela: Scene 1: stairwell, 15:00–15:15; camera_sound; kit sound_recorder; Scene 2: courtyard, 15:25–15:35; camera_sound; kit sound_recorder; Scene 3: rooftop, 16:45–18:15; camera_sound; kit sound_recorder; Call 14:45 (was unconfirmed).

4. **proposal ? ad-human ? option 1** ? Maya says: 'I have to leave at 6'. Record `person maya hard_stop 18:00`?

5. **duty ? dev ? option 2** ? Release 2 · Dev: Scene 3: rooftop → stairwell; Scene 3: end 18:15 → 18:00; Call 14:45 (was 14:45).

6. **proposal ? ad-human ? option 1** ? Dev says: 'Running 40 min late'. Record `person dev late_by 40`?

7. **duty ? maya ? option 1** ? Release 3 · Maya: Scene 2: start 15:25 → 16:05; Scene 2: end 15:35 → 16:15; Scene 3: rooftop → stairwell; Scene 3: end 18:15 → 18:00; Call 16:05 (was 15:25).

8. **duty ? dev ? option 1** ? Release 3 · Dev: Scene 1: start 15:00 → 15:40; Scene 1: end 15:15 → 15:55; Scene 2: start 15:25 → 16:05; Scene 2: end 15:35 → 16:15; Scene 3: rooftop → stairwell; Scene 3: end 18:15 → 18:00; Call 15:25 (was 14:45).

9. **duty ? leela ? option 1** ? Release 3 · Leela: Scene 1: start 15:00 → 15:40; Scene 1: end 15:15 → 15:55; Scene 2: start 15:25 → 16:05; Scene 2: end 15:35 → 16:15; Scene 3: rooftop → stairwell; Scene 3: end 18:15 → 18:00; Call 15:25 (was 14:45).

10. **duty ? leela ? option 1** ? Release 4 · Leela: Scene 1: kit sound_recorder → lav; Scene 2: kit sound_recorder → lav; Scene 3: kit sound_recorder → lav; Call 15:25 (was 15:25).

11. **duty ? maya ? option 1** ? Release 5 · Maya: Scene 2: start 16:05 → 16:20; Scene 2: end 16:15 → 16:30; Call 16:20 (was 16:05).

12. **duty ? dev ? option 1** ? Release 5 · Dev: Scene 1: end 15:55 → 16:20; Scene 2: start 16:05 → 16:20; Scene 2: end 16:15 → 16:30; Call 15:25 (was 15:25).

13. **duty ? leela ? option 1** ? Release 5 · Leela: Scene 1: end 15:55 → 16:20; Scene 2: start 16:05 → 16:20; Scene 2: end 16:15 → 16:30; Call 15:25 (was 15:25).

The r2 Maya and Leela cards were open until the Dev report superseded that plan:

- `Release 2 ? Maya: Scene 3: rooftop ? stairwell; Scene 3: end 18:15 ? 18:00; Call 15:25 (was 15:25).`
- `Release 2 ? Leela: Scene 3: rooftop ? stairwell; Scene 3: end 18:15 ? 18:00; Call 14:45 (was 14:45).`

Dev selected Can't make it with the exact custom note **Running 40 min late**. The AD selected Record on both proposed changes. Headless Microsoft Edge opened the final live Control Room, found release 5, and reported no page errors; screenshot: `data/w8-review.png`. Neither pending report changed facts before that authenticated answer.

## 2. Runtime facts learned

- Real Switch `GET http://127.0.0.1:8000/health` returned `200 {"status":"ok"}`; Mattermost `:8065/api/v4/system/ping` returned 200 with status OK. Rehearsal HTTP used :8789; final review uses :8787. Docker named-pipe access is denied to this sandbox, but the already-running services are reachable over HTTP. My initial port-inventory inference was wrong and was corrected before testing.
- Mattermost rendered native single-choice requests with handles such as `A?`; simulated people used the real typed form `A? q1=1` or `A? q1=2, "Running 40 min late"`. Switch's stored native answer uses snake-case keys: `{"custom_text":"Running 40 min late","question_id":"choice","selected_option_ids":["cannot"]}`. The coordinator handles both source-supported naming forms.
- **Source wins:** `E:/DevDrive/switch/core/switch_core/session_activity/service.py:465` authorizes answering by the agent's addressing policy, not the named crew person. The coordinator independently rejects an incorrect sender and permits exactly one replacement within the original expiry. No per-card film-person ACL is claimed. `service.py:717` clips prompts at 4000 characters; all observed personal prompts fit intact.
- Discord single-choice buttons are source-supported by `bridges/collaboration/discord/adapter.py:1455`, conditional on bridge setup. No Discord bridge is configured here, so Discord is **untested**. This is real Switch/Mattermost transport with simulated workers and people; no real model reasoning or Discord delivery is claimed.
- The W6 call-only acknowledgment contract was intentionally replaced by the W8 duties contract. No additional Switch protocol/source disagreement was discovered. Publication still means accepted by Switch for relay.
- Fresh replay `npm ci` succeeded. Both standard and native-config-loader Vite launches hit esbuild's denied parent-directory read in this restricted environment. No UI source or dependency workaround is shipped to disguise that limitation.

## 3. Needs the human

1. Verify the outstanding fresh-copy browser step in normal PowerShell: from this repo run `npm run dev --prefix data/w8-clean-replay/ui`, open `http://localhost:5173/?fixtures=day` in Edge, and step through all 26 moments. The sandbox cannot establish this result. The fresh install is already present; no token is needed.
2. Read this report and review the changes; Claude owns commits. The current-code review server is running on `http://127.0.0.1:8787/` with r5. Its state API and rendered media are available independently of the UI build. For a fresh machine use the two paths in `QUICKSTART.md`; credentials are generated privately by the listed commands, not copied into chat.
3. For a real crew/provider demo beyond this acceptance path, configure Discord and real role workers through `docs/SETUP-HUMAN.md`, then test a crew account's button, PNG and MP4. W8's rehearsal requires no Discord account or agent subscription.

## 4. Found, not fixed

- `ui/src/components/Side.tsx:161` still explains carry-forward as ?Their call time did not change.? Its owner should change that wording to duties and render `duty_changes` / `since_confirmed`; the W8 contract is documented in `docs/UI-CONTRACT.md`. UI edits were forbidden for this worker.
- `ui/src/types.ts:107` / `:117` do not declare the optional new personal fields or pending-report resolution. The UI owner should add them and use `resolution` to distinguish recorded/dismissed reports from outstanding ones. The API retains the original pending report for audit and adds a separate authenticated fact change.
- `coordinator/dispatcher.py:306` still leaves uncertain release-media delivery for human review. Only immutable question opens gained safe restart retry; authenticated media reconciliation is an existing follow-up, with no blind resend added.
- `QUICKSTART.md:17`: clean-install replay browser verification is blocked by sandbox esbuild permissions, not proven. Run the exact documented command outside the sandbox; do not call the replay acceptance complete until it opens.

## 5. Self-review

Re-read all W8 implementation files and the altered integration paths without git. A fresh read-only reviewer was dispatched under the code-review skill; I reviewed its findings against the brief. Its whitespace-note failure and partial time-parse findings were reproduced with failing tests and fixed. A dismissed report before /plan was also verified not to block initial planning (`coordinator/planning.py:17`). The reviewer declined live Discord, clean browser replay and live reproducibility: Discord remains untested, replay remains blocked, and real reproducibility was independently exercised twice by the driver.

Five ways I tried to break it:

1. Kept calls unchanged while relocating s3, changed recorder to lav, and left Maya on an older confirmed baseline. New audiences include every changed duty; Leela alone owns kit changes; personal differences do not use the globally previous release.
2. Answered Maya's card as Dev, consumed its replacement as Leela, replayed old/superseded/revision-stale outcomes, and replayed a processed native answer after restart. No incorrect ack/fact/release was accepted; replacement count remains one.
3. Selected Can't make it with an explanatory note and with whitespace; answered a proposed change as the director instead of the AD; then selected Ignore as the AD. Notes remain valid pending reports, wrong authority changes nothing, and Ignore dismisses without applying facts.
4. Tried unknown names/kit/fields, confidence 0.5, uncertain times, clock ranges, seconds, another timezone/date, invented window endpoints, unknown availability, and truncation hiding a later alternative. No authority card is offered for those interpretations; uncertain reports stay pending.
5. Sent malformed extraction schemas and ambiguous bad JSON while multiple first-ad jobs were active, forced a restart after a question send became uncertain, and replayed the authority Record result after restart. Retries remain capped/backed off, failures have timeline and visible messages, exact request retries are idempotent, and Record/ack/outcome/delivered effects share the durable transaction.

Invariant audit: (1) approvals and revision checks still gate releases; (2) SQLite outcome/effect transactions preserve decisions and dedupe; (3) Switch identity plus configured authority gates facts/releases; (4) expiry selects nothing; (5) new failure paths add timeline and visible outbox messages; (6) jobs, payloads, request history and replacements are bounded; (7) malformed agent replies use the one-retry path and cannot mutate facts. These are tested guarantees within the supplied workflow, not a claim of untested Discord delivery.

Final evidence check: both `work/W8-final-real-1.log` and `work/W8-final-real-2.log` end with r5 / 26 beats / normalized_match=true. `data/w8-checks.json` records the 26 strict snapshots, unchanged original examples, LF/line-limit checks and HTTP 200 review state. No code or runtime acceptance item is represented as completing the blocked fresh-copy Vite browser check.
