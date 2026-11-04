# W4 report

Final verification complete: 235 tests passed and two final-code rehearsals against real Switch/Mattermost produced identical summaries and complete release-manifest hashes.

## 1. Done

`$env:UV_CACHE_DIR='data/uv-cache'; uv run pytest -q`: **235 passed, 1 skipped, 1 warning**. Python 3.12.10; `pyproject.toml` restricts Python to 3.12. The existing skip requires Windows symlink permission; the warning is Starlette's deprecated AnyIO alias. Output: `data/w4-final-tests.txt`.

The real-server driver is `scripts/demo_dry_run.py:99`. It registers separate worker agents and Mattermost people, sends the initial command through `scripts/seed_initial_plan.py:23`, gets native Mattermost answers, renders actual media, uploads it through Switch, and reads the local HTTP `/api/state`. It never calls Loop transition methods. It uses a private production room named **w4-production**, with a separate ledger under `data/w4-demo`; the original `data/ledger.sqlite` and `data/identity.json` are preserved.

Acceptance coverage:

| Acceptance item | Implementation | Proof |
|---|---|---|
| Addressed, fenced worker replies; bounded ambiguity handling | `coordinator/worker_text.py:18`, `coordinator/loop.py:198` | `test_real_worker_mention_fence`, `test_ambiguous_or_unbounded_reply_is_rejected`; both real workers in the dry run |
| Trusted render props, complete manifest identity, diagnostics and renderer limits | `coordinator/render_props.py:9`, `coordinator/release.py:38`, `coordinator/render_bridge.py:30`, `coordinator/render_schema.py:18` | `test_preview_uses_trusted_names_and_candidate_identity`, `test_render_hashes_manifest_writes_props_and_retains_last_error`, `test_callsheet_complete_and_held_rows_are_strict`, `test_generated_props_are_accepted_by_real_zod_schemas` |
| One complete initial schedule, one approval, r1; shoot-day provision or visible absence | `coordinator/planning.py:11`, `coordinator/rooms.py:17`, `fixtures/film/constraints-r1.yaml:42` | `test_one_initial_approval_commits_complete_r1_and_repeat_command_is_deduped`, `test_discord_day_room_uses_template_and_owns_document`, `test_no_discord_bridge_is_visible_and_idempotent` |
| Authenticated `/plan day-1`, no browser authorization | `coordinator/runtime.py:266`, `scripts/seed_initial_plan.py:23` | Unauthorized initial command rejected by the initial-plan test; real Mattermost command in each run |
| Scene 2 remains valid; unresolved scenes persist; replaced commitments are freed | `coordinator/planning.py:29`, `coordinator/schedules.py:21` | `test_hard_stop_does_not_hold_scene2_and_unresolved_scope_survives`, `test_replacing_scene_frees_its_old_commitment`, `test_unrelated_safety_hold_is_preserved_in_release` |
| Script cast and required capabilities cannot be omitted; must_keep is retained and shown honestly | `coordinator/runtime.py:117`, `coordinator/checker.py:107`, `coordinator/loop.py:264` | `test_trusted_cast_and_kit_cannot_be_omitted`, `test_decision_uploads_two_bound_previews_before_native_card` |
| Both MP4s and checked summaries precede the native card | `coordinator/dispatcher.py:220` | `test_decision_uploads_two_bound_previews_before_native_card`, `test_uncertain_preview_upload_never_opens_or_retries_card`; driver waits for the actual first card before the newer change |
| Named crew text, production day label, backed-up reset | `coordinator/render_props.py:77`, `coordinator/runtime.py:325`, `scripts/reset_demo.py:8` | `test_complete_release_is_immutable_and_text_uses_trusted_metadata`, `test_reset_backs_up_ledger_and_preserves_identity`; actual blue r2 PNG visually inspected |
| Reconnect barrier and immediate pause | `coordinator/recovery.py:14`, `coordinator/recovery.py:20`, `coordinator/switch_client.py:348` | `test_offline_refusal_precedes_owed_answer_and_dispatch`, `test_transport_loss_during_outcome_fetch_cannot_reenable_old_barrier`, `test_heartbeat_lapse_pauses_before_reconnect_without_terminal_frame` |
| Timely server answers delivered after local expiry are honored | `coordinator/loop.py:303` | `test_timely_server_answer_after_local_expiry_is_honoured`, `test_expired_server_outcome_never_reissues_and_is_visible` |
| Publication terminology is honest; bridge errors reach state | `coordinator/release.py:103`, `coordinator/runtime.py:284`, `scripts/README.md:13` | `test_room_release_pauses_and_bridge_failure_is_visible`; `sent` explicitly means accepted by Switch for relay |
| Browser reports cannot confirm, clear holds, or authorize release | `coordinator/runtime.py:346`, `coordinator/loop.py:118` | `test_browser_refusal_holds_and_cannot_confirm_or_clear` |
| Oversized input and duplicate manifest identities cannot strand completed jobs | `coordinator/loop.py:198`, `coordinator/constraints.py:119`, `coordinator/ledger.py:176` | `test_oversized_worker_frame_gets_one_retry_instead_of_quarantine`, `test_trusted_fixture_counts_fit_renderer`, `test_long_failure_diagnostic_fits_state_instead_of_crashing`, `test_identical_manifests_with_distinct_labels_do_not_strand_previews` |

Final real-server evidence is saved as `data/w4-demo/verified-run-1.json`, `verified-run-2.json`, their `.log` files, and `comparison.json`. Verified identical normalized result: script 1 / constraints 3, r2 published to Mattermost, all three scenes valid, stairwell / courtyard / stairwell, Dev's stale reply corrected, and Dev / Leela / Maya confirmed. Each run has two preview rounds with two successful MP4s each, two call-sheet PNGs, and exactly r1 then r2. The complete r2 manifest digest is `sha256:e93ea6b64577d417c5cf49824728769416ae268d8138e5aba48cd925785a01dc`.

Operations: W1 PID **28140** was stopped with the explicit authorization in the brief. Only task-owned test/server processes were otherwise stopped. A review server using the verified rehearsal ledger is running on **http://127.0.0.1:8787** (Python PID **51872**, uv launcher **17428**). The page, state, PNG and MP4 returned HTTP 200; evidence is in `data/w4-demo/review-server-check.json`. This is the real Switch rehearsal, with simulated people and workers, rather than the original production ledger.

No git commands or global installations. Renderer dependencies were installed locally under `data/renderer-runtime` (264 npm packages); the fixed renderer, browser files and bundle cache stay under `data`. No edits to Switch, `render/`, `ui/`, `agents/`, or `docs/`. Authored Python files use LF and stay below 500 lines. Credentials remain in ignored `.env` / persisted identity files; no credential values are included here.

## 2. Runtime facts learned

- Real endpoints: Switch API and sockets at `127.0.0.1:8000`; Mattermost at `127.0.0.1:8065`; Gateway API under `/gateway` on port 8000. Native media uses multipart `POST /agents/{id}/rooms/{room}/media`, returning `event_id`, `mxc`, and `attachments`.
- **Source wins:** new agents default to owner-only addressing. A newly registered test director was refused by Switch with “you may not address this agent, so you may not answer it.” The rehearsal agent now has an explicit policy scoped to its private test room; Loop still checks the named director. Worker names, agent UUIDs, and transport sender identities are different values. `sender_kind` can be null. Roles are checked using registered worker names.
- **Source wins:** question opening JSON uses snake_case; HTTP outcome views use camelCase; stored question answers use `question_id`, `selected_option_ids`, `custom_text`. A native typed answer such as `A<number> q1=2, "keep the confession private"` is accepted through Mattermost. Request handles are visible in the card; the card body does not expose its request UUID.
- **Source wins:** `questions[].prompt` and option descriptions carry the visible question content. Top-level `detail` alone does not display Supervisor requirements on a questions card. The requirements are therefore also placed in the prompt, explicitly described as prose for human review, not machine-checked requirements.
- **Source wins:** connection_state is the starting baseline, not a catch-up acknowledgment. The implementation samples an authoritative own-event head and reconciles bounded room history before outcomes. Transport loss clears the admission barrier immediately. `heartbeat_lapsed` is recoverable; `taken_over` stays terminal. A direct 12-second real probe retained its role with normal socket heartbeats. Rehearsal streams refresh their own role at readiness and after reconnect; blocking setup work runs outside their event loop.
- No Discord bridge is configured. The visible state is “No Discord bridge yet”; no Discord playback or external delivery was claimed. `published` uses the existing contract's Switch-acceptance threshold. Bridge delivery errors become timeline items.
- The C3 example's 16:15 crew calls would miss earlier scenes. The actual complete schedule gives Maya 15:25 and Dev / Leela 14:45. These are derived from the earliest duty including setup, and are present in the inspected call sheet.
- C6 evidence: the original ledger contains **two failed message effects with an empty room_id and only SwitchError recorded**. The old logger discarded the HTTP status, so a membership error cannot be established retrospectively. Future diagnostics include status, destination and safe refusal detail. The old ledger remains available for review.
- License checked at `E:/DevDrive/switch/LICENSE:4`: Apache 2.0 **as limited by the modified Commons Clause**.

## 3. Needs the human

No accounts, tokens or clicks are needed to finish viewing this rehearsal. Open the Control Room in Edge at `http://127.0.0.1:8787`. The real Mattermost room is `http://localhost:8065/switch/channels/w4-production`; test-person credentials are in `data/w4-demo/.env`.

For the actual crew workflow:

1. Connect two real Console identities, assign `script-supervisor` and `first-ad`, and permit coordinator addressing. Configure their registered names and authenticated transport sender IDs, plus the real director, producer, availability and safety authorities in the original `.env`.
2. Configure the Discord bridge in Switch, grant its required channel/file permissions, link the owner's Discord account, and supply the bridge display name and the template's three crew usernames through `TAKE_TWO_DISCORD_BRIDGE` and `TAKE_TWO_DAY_ACTOR/CAMERA/SOUND`.
3. Stop the rehearsal review server before switching to the normal coordinator. To start from W1's smoke ledger, run `uv run python -m scripts.reset_demo`; it backs up the ledger and preserves identity and rooms. Configure artifact/CLI paths under `data`, then start `uv run python -m coordinator`.
4. As the director, type `/plan day-1` in Mattermost. Alternatively configure the director's Mattermost credentials and channel ID described in `scripts/README.md`, then run `uv run python -m scripts.seed_initial_plan`. Workers propose, the checker checks, and the director approves the native card once.
5. Before using the real shoot, open an uploaded PNG and MP4 from a real crew Discord account. Switch acceptance is not that test.

Claude owns the commit and the next review. No W4 review beyond the supplied C1-C7 / F1-F20 reviews has been received yet.

## 4. Finding reconciliation and found, not fixed

Test names above are exact pytest function names under `coordinator/tests/`. Bare module paths in the table below are relative to `coordinator/`. Deferred items remain deliberately conservative and visible.

| Finding ID | Status | File:line and proving test / suggested remaining work |
|---|---|---|
| C1, F2, F14 | Fixed | `render_props.py:9`, `release.py:38`, `schedules.py:46`; `test_generated_props_are_accepted_by_real_zod_schemas`, `test_complete_release_is_immutable_and_text_uses_trusted_metadata` |
| C2, F19 | Fixed | `render_bridge.py:58`, `dispatcher.py:356`, `ledger.py:176`; `test_render_hashes_manifest_writes_props_and_retains_last_error`, `test_long_failure_diagnostic_fits_state_instead_of_crashing` |
| C3 | Fixed | `render_props.py:77`, `planning.py:45`, `runtime.py:325`; `test_complete_release_is_immutable_and_text_uses_trusted_metadata` and real Dev correction |
| C4 | Fixed | `runtime.py:95`; `test_complete_release_is_immutable_and_text_uses_trusted_metadata` |
| C5 | Fixed | `scripts/reset_demo.py:8`, `scripts/README.md:5`; `test_reset_backs_up_ledger_and_preserves_identity` |
| C6 | Diagnosed; future diagnostics fixed | `dispatcher.py:356`; original-ledger SQL evidence above; `test_failure_is_visible_in_production_and_notice_failure_does_not_recurse` |
| C7, F1 | Fixed | `worker_text.py:18`, `loop.py:198`; `test_real_worker_mention_fence`, `test_ambiguous_or_unbounded_reply_is_rejected`; real worker handoffs |
| F3 | Fixed | `recovery.py:14`, `switch_client.py:348`; `test_offline_refusal_precedes_owed_answer_and_dispatch`, `test_transport_loss_during_outcome_fetch_cannot_reenable_old_barrier`, `test_heartbeat_lapse_pauses_before_reconnect_without_terminal_frame` |
| F4 | Fixed | `planning.py:11`, `rooms.py:17`, `scripts/seed_initial_plan.py:23`; `test_one_initial_approval_commits_complete_r1_and_repeat_command_is_deduped`, `test_discord_day_room_uses_template_and_owns_document`; real r1 approval |
| F5 | Fixed | `planning.py:29`; `test_hard_stop_does_not_hold_scene2_and_unresolved_scope_survives`, `test_unrelated_safety_hold_is_preserved_in_release` |
| F6 | Fixed | `checker.py:107`, `runtime.py:117`, `loop.py:264`; `test_trusted_cast_and_kit_cannot_be_omitted`, `test_decision_uploads_two_bound_previews_before_native_card`. Supervisor prose is explicitly not machine-checked |
| F7 | Fixed | `dispatcher.py:220`; `test_decision_uploads_two_bound_previews_before_native_card`, `test_uncertain_preview_upload_never_opens_or_retries_card` |
| F8 | Fixed | `loop.py:303`; `test_timely_server_answer_after_local_expiry_is_honoured`, `test_expired_server_outcome_never_reissues_and_is_visible` |
| F9 | Deferred as requested | `dispatcher.py:297`; add authenticated reconciliation/resolution for uncertain publications, then bounded same-ID retries. `test_restart_does_not_resend_uncertain_media_and_reports_room` proves uncertain media is not blindly resent |
| F10 | Fixed to W4 semantics | `release.py:103`, `runtime.py:284`, `scripts/README.md:13`; `test_room_release_pauses_and_bridge_failure_is_visible`; accepted-for-relay terminology |
| F11 | Deferred as requested | `dispatcher.py:249`, `runtime.py:305`; persist/map media receipt and thread roots, as text roots already are |
| F12 | Visible failure fixed; verification workflow deferred | `loop.py:257`; `test_trusted_cast_and_kit_cannot_be_omitted` proves “No feasible option” reaches production. Add authority-bound verification requests and full candidate projection later |
| F13 | Partial; full refactor deferred | `loop.py:69`, `release.py:38`; canonical plans and call times are fixed. Remaining: scene-field projection, accurate prepared/open/running phases, ack deadline/policy and explicit carry-forward records |
| F15 | Fixed | `runtime.py:346`; `test_browser_refusal_holds_and_cannot_confirm_or_clear` |
| F16 | Fixed | `schedules.py:21`; `test_replacing_scene_frees_its_old_commitment` |
| F17 | Fixed | `constraints.py:119`, `loop.py:198`, `ledger.py:176`; `test_trusted_fixture_counts_fit_renderer`, `test_oversized_worker_frame_gets_one_retry_instead_of_quarantine`, `test_long_failure_diagnostic_fits_state_instead_of_crashing`, `test_identical_manifests_with_distinct_labels_do_not_strand_previews` |
| F18 | Deferred as requested | `loop.py:335`, `switch_client.py:280`; cap automatic unauthorized reissues within the original deadline, and archive question/workflow caches while retaining decision dedupe |
| F20 | Crew text fixed; cleanup deferred | `runtime.py:352`, `switch_client.py:280`, `workflow_models.py:68`; consolidate remaining duplicate state/cache machinery, unused helpers/settings, and explicit logistics bypass |

Read-only follow-ups: document the new `Candidate.schedule`, `Decision.must_keep` and `requirements_note` fields in `docs/UI-CONTRACT.md`; document publication acceptance and `/plan`; add the initial `manifests` array shape to `agents/first-ad.md`; link `scripts/README.md` from the root README. Native answer text and Switch document notices can still become harmless pending-report noise (`runtime.py:352`); filter these without suppressing genuine crew reports.

The real Discord provisioning branch has unit coverage and was not exercised against a connected Discord bridge. No manual uncertain-publication resolution or media-root stale-reply support is claimed.

## 5. Self-review

Re-read the complete filesystem diff without git. Fixed additional audit issues found during that pass: settled question rows now retain answered status, including “Neither + note”; identical manifests with distinct labels have separate preview effects; oversized diagnostics cannot overflow the State timeline field.

Five break attempts:

1. Sent mention/fence envelopes, duplicate objects/keys, nonfinite JSON, malformed text and oversized worker frames. They parse only when unambiguous; bad replies get one retry and visible failure.
2. Removed Maya and the recorder, moved a replacement over retained work, changed the hard stop, and refused a pending candidate's location. Hard checks fail omissions/conflicts, Scene 2 remains usable, and unresolved work survives revisions.
3. Combined an offline refusal with an owed answer, then lost transport during outcome fetch and exercised heartbeat expiry. Effects stay paused until the new barrier is valid; stale decisions cannot send a crew release.
4. Replayed outcomes, used unauthorized and expired answers, delivered a timely answer late, and checked answered question rows after both release and Neither. No duplicate release or reopened answered request; silence chooses nothing.
5. Failed preview upload, supplied a wrong/traversing media path, generated strict-schema props and long renderer diagnostics, and proposed identical manifests with different labels. No unsafe media send, hidden defaults, premature card opening or stranded preview remains in these cases.

Invariant audit: approved/revision-bound manifests gate crew effects; decisions/outcomes/outbox commit durably; named authorities gate release; expiry never selects; failures reach the timeline and visible notices; per-job/network/render/queue/payload work is bounded; malformed worker text cannot escape the validation/retry path. **F18 remains an explicit exception to the lifecycle-bound requirement**: automatic unauthorized-card reissues and persisted cache growth still need the deferred cap/archive work. F9's unresolved publication remains uncertain rather than being falsely declared delivered.
