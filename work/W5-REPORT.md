# W5 report

## 1. Done

`uv run pytest -q`: **256 passed, 1 skipped, 1 warning**, with no environment overrides or extra command flags. Evidence: `data/w5-final-tests.txt`. The existing skip needs Windows symlink permission; the existing warning is Starlette's deprecated AnyIO alias. Python remains restricted to 3.12 in `pyproject.toml:5`.

| Acceptance item | Implementation | Proof |
|---|---|---|
| Coordinator/worker/system/document chatter and native answers never become reports; only known humans' unconsumed free text does | `coordinator/runtime.py:309`, `coordinator/runtime.py:370`, `coordinator/switch_text_answer.py:134` | `test_w4_chatter_never_becomes_report_but_maya_does_once`, `test_exact_w4_ledger_reports_replay_without_coordinator_noise`, `test_consumed_question_message_never_becomes_report`, `test_system_kind_cannot_become_human_report` |
| One pending report per message, including replay/restart; trusted reporter names | `coordinator/runtime.py:378` | `test_pending_report_is_deduped_across_restart_and_history`, `test_known_authority_report_uses_configured_name_not_message_name`; 37 exact persisted W4 report values in `fixtures/w5-room-chatter.json:1` replay to just Maya's report |
| No lone surrogates enter transport models, UI state, or the ledger | `coordinator/switch_client.py:174`, `coordinator/switch_models.py:76`, `coordinator/ui_models.py:29`, `coordinator/unicode_text.py:5` | `test_http_multibyte_punctuation_split_across_chunks`, `test_websocket_multibyte_punctuation_split_across_frames`, `test_http_escaped_lone_surrogate_is_rejected_at_ingress`, `test_worker_escaped_surrogate_gets_one_retry_then_visible_failure` |
| Additive decision/answer/reporter/crew/room display fields; generated timeline text uses trusted names | `coordinator/ui_models.py:77`, `coordinator/runtime.py:150`, `coordinator/loop.py:295`, `coordinator/loop.py:376`, `coordinator/release.py:69`, `coordinator/rooms.py:38` | `test_decision_change_release_and_roles_have_trusted_names`; both real rehearsals and final HTTP state verification |
| Preserve typed time values and expose the checker's production-day timestamp | `coordinator/loop.py:147`, `coordinator/presentation.py:26` | `test_time_change_exposes_checker_time_and_keeps_typed_value` covers HH:mm, light cutoff, and UTC input; live hard stop is `value: "18:00"`, `at: "2026-11-06T18:00:00+05:30"`. Additive `recorded_at` preserves ingestion time |
| Clean-shell pytest works; locked old test directories repaired | `pyproject.toml:20`, `coordinator/tests/conftest.py:8` | Plain command above; uv cache is project-local, pytest cache is disabled, and each run has a fresh temp root. Inherited ACLs restored recursively only under resolved `data/pytest-*` directories, without deleting files. Logs: `data/w5-acl-repair-all.log` |
| Malformed replies select a job by authenticated sender role before charging a retry; hhmm import is at module scope | `coordinator/loop.py:23`, `coordinator/loop.py:217` | `test_malformed_worker_selects_sender_role_before_newest_job`, `test_role_selection_with_two_active_jobs_cannot_retry_another_worker` |
| Enforce the 45-second catch-up deadline, including history, outcome fetching, and outcome processing; late fences cannot restore readiness | `coordinator/recovery.py:22`, `coordinator/recovery.py:33`, `coordinator/recovery.py:71`, `coordinator/runtime.py:407` | `test_catchup_deadline_blocks_late_fence_and_outcome`, `test_catchup_outcome_fetch_cannot_overrun_deadline`, `test_catchup_outcome_processing_cannot_overrun_deadline`; exactly one visible error plus a queued production notice, with effects paused |
| Document all W4/W5 fields and publication semantics | `docs/UI-CONTRACT.md:46`, `docs/UI-CONTRACT.md:105` | Contract includes `Candidate.schedule`, `Decision.must_keep`, `Decision.requirements_note`, every W5 field, and explicitly says published means accepted by Switch for relay, not delivered |
| Two reset rehearsals against real Switch and a review server | `scripts/demo_dry_run.py:110`, `scripts/demo_dry_run.py:218`, `work/W5-verify.py:52` | Ran `uv run python -m scripts.demo_dry_run` twice from its backed-up reset, then `uv run python -m work.W5-verify`. Evidence below |

Final rehearsal evidence: `data/w5-final-run-1.json`, `data/w5-final-run-2.json`, and their `.log` files. Both produced identical summaries and complete r2 manifest hash `sha256:e93ea6b64577d417c5cf49824728769416ae268d8138e5aba48cd925785a01dc`. Each exercised initial approval/r1, rooftop refusal, two preview rounds, hard-stop invalidation, native director approval/r2, Dev's stale-reply correction, and three current confirmations. These are real Switch/Mattermost transports with simulated people and worker proposals, as in W4.

The final HTTP state is saved to **`work/W5-state.json:1`**. It has exactly three changes (Nila's permission change, Maya's pending report, Isha's hard stop), zero coordinator reports, zero lone surrogates or literal `\\udc` sequences, all new display fields, and 38 timeline items with exactly one reported-change item. Verification checks known local credentials are absent; it does not redact credentials into the artifact. `data/w5-verification.json` records the checks.

Review server: **http://127.0.0.1:8787**, Python PID **22292**, running `scripts.serve_demo` through the task's managed process session. Process details and the equivalent restart command are in `data/w5-review-process.json`. The page, API, final PNG and MP4 returned HTTP 200. The server reconnected to real Switch using the final rehearsal ledger. Only the explicitly authorized W4 Python PID 51872 and uv PID 17428 were stopped; rehearsal/test servers shut down their own processes. Docker/Switch was already running and was not started or stopped.

No git commands, commits, global installs, Chrome, or edits to Switch, `ui/`, `render/`, or `agents/`. Authored source/artifact files use LF and remain below 500 lines; the state artifact uses compact JSON. The only docs edit is the UI contract. The filesystem diff is in `data/w5-diff.txt`, generated against the initial source copies without git.

## 2. Runtime facts learned

- Real endpoints remain Switch HTTP/WebSocket on `127.0.0.1:8000` and Mattermost on `127.0.0.1:8065`; health/ping returned HTTP 200.
- **Source wins:** Switch UUIDs and chat sender identities differ; `sender_kind` may be null. The rehearsal now resolves the coordinator's sender from its own message receipt matched against `read_context` (`scripts/demo_dry_run.py:83`). Trying to discover it from a live self-echo timed out, so that assumption was removed before the two successful final runs.
- **Source wins:** typed native answers are relayed alongside the native question outcome, with no consumed-message flag. See Switch `core/switch_core/bridges/collaboration/collaboration_core.py:1958`. W5 reuses the pinned source's bounded answer parser instead of inventing another grammar or relying on a nonexistent flag. Source and license attribution are retained in `coordinator/switch_text_answer.py:1`, `coordinator/SWITCH-LICENSE.txt`, and `coordinator/SWITCH-NOTICE.txt`.
- The archived W4 state and its 37 report values contain valid Unicode closing quotes (`U+201D`); I did not reproduce the reported lone surrogate in persisted data or find `surrogateescape` in the coordinator. HTTP already assembled byte chunks before JSON parsing, and websockets reassembles fragmented text. W5 makes strict UTF-8 decoding/Unicode validation explicit at ingress, rejects escaped lone surrogates before persistence, and proves punctuation survives both one-byte HTTP chunks and fragmented WebSocket frames. The origin of the earlier observed display damage is unproven.
- No Discord bridge is configured. This rehearsal publishes to the private Mattermost room `w4-production`, displayed by its configured production alias `#production`. Switch acceptance and HTTP media retrieval do not prove Discord delivery or playback.

## 3. Needs the human

For W5 review, no accounts, tokens, or setup clicks are required:

1. Open **http://127.0.0.1:8787** in Edge. Inspect the three changes, named decision/answer, crew role labels, publications, and timeline. `work/W5-state.json` is the saved public snapshot.
2. Claude reviews the diff and this report, supplies any review findings, and commits the approved changes. No new Claude review was available to review in this turn.

For the actual crew workflow, the remaining W4 setup still applies:

1. Connect the real Console workers and configure their roles, permitted coordinator addressing, authenticated sender IDs, and named human authorities in ignored configuration.
2. Configure the Discord bridge, link the owner's Discord identity, grant channel/file permissions, and configure the reviewed crew usernames. Set `TAKE_TWO_COORDINATOR_SENDER_ID` to the coordinator's authenticated transport sender; use `TAKE_TWO_ROOM_NAMES` for explicit destination labels when needed. Credentials stay in ignored files.
3. Switch from this rehearsal ledger to the intended production configuration, then verify PNG opening and MP4 playback from a real crew Discord account before the shoot.

## 4. Found, not fixed

- **Earlier encoding symptom:** no corrupt stored quote was found. The earlier display layer that produced `\udc9d` remains unidentified; capture raw HTTP bytes from that exact failing surface if it recurs. The coordinator now rejects malformed Unicode and the final snapshot is clean. Relevant boundary: `coordinator/switch_client.py:174`.
- **W4 F18:** unauthorized answers can still cause uncapped replacement cards (`coordinator/loop.py:346`), and the question cache grows across resets (`coordinator/switch_client.py:282`). Suggested fix: cap reissues within the original deadline and archive settled payloads while retaining dedupe. W5's per-job retry change and catch-up timeout do not solve this existing lifecycle issue.
- **W4 F9/F11:** uncertain-publication reconciliation remains manual (`coordinator/dispatcher.py:306`), and stale-reply receipt mapping still covers text roots rather than every media root (`coordinator/dispatcher.py:374`). Suggested fix: add authenticated resolution plus persisted media/thread receipt mapping. Uncertain media is not blindly resent.
- **Legacy snapshots:** the additive name fields are optional for backwards compatibility (`coordinator/ui_models.py:77`). W5 creates them for new live objects and its reset rehearsal; it does not rewrite historical ledgers, erase old false reports, or modify the read-only UI. The original W4 ledger was backed up before resetting the isolated rehearsal database.

## 5. Self-review

Re-read the complete filesystem diff and copied parser, plus the real HTTP state. During this pass I extended the deadline over outcome processing itself, checked coordinator/crew identity collisions, retained upstream notices, and replaced the rehearsal's invalid self-echo assumption with receipt-matched history.

Five break attempts:

1. Replayed 37 exact W4 report values plus worker replies, null sender kinds, system notices, card answers, unknown senders and malformed commands. Only Maya's genuine report survives; replay/restart cannot duplicate it. Even a coordinator sender mistakenly mapped to crew is excluded.
2. Spoofed a display name in chat and exercised configured authority/crew aliases. Names remain fixture/config-derived; decision/answer/report/role/room displays are populated independently of authorization IDs.
3. Split curly punctuation inside its UTF-8 bytes over HTTP chunks and WebSocket frames, then supplied an escaped lone surrogate. Valid text survives; malformed text cannot enter state or persistence. Malformed worker text follows the bounded retry/failure path.
4. Delivered malformed replies from the wrong worker and with two active job roles. A sender can spend only its own current job's retry; a completed Supervisor cannot burn the AD retry. After one retry, the failure is visible.
5. Delivered the catch-up fence after expiry and blocked both outcome fetching and processing past the deadline. Exactly one timeout error is recorded, its notice is durable, and effects remain paused. The existing suite also exercises stale revisions, duplicate/unauthorized/expired outcomes, publication failures, and browser impersonation.

Must-never audit: (1) checked revision-bound candidates still gate crew release; (2) inbox/outcomes/outbox remain durable and replay tests pass; (3) named authority checks are unchanged and tested; (4) expiry never chooses an option; (5) timeout/validation failures are visible; (6) new work has bounded parsing/retries/deadlines, **with the pre-existing F18 lifecycle exception above**; (7) malformed agent JSON still receives at most one retry before visible failure. No claim is made that the deferred W4 findings have been solved.
