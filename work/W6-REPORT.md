# W6 report

## 1. Done

`uv run pytest -q`: **286 passed, 1 skipped, 1 warning** (120.28 seconds). The existing skip requires Windows symlink permission; the existing warning is Starlette's deprecated AnyIO alias. Full output: `data/w6-final-tests.txt`. Python remains pinned to 3.12 by `pyproject.toml:5`.

W5 was committed on main before W6 began: `0a966b9`, “Live state reads like a production office,” verified from the local ref/reflog files without git commands. Switch is still `989225d8a13f6f36359c54f52d86aec01c4e0826`, also read directly from its ref file. Its LICENSE is Apache-2.0 with the modified Commons Clause. Existing public-client/rehearsal code is reused and attributed in `scripts/day_workers.py:1` and `scripts/demo_day.py:1`.

| Acceptance item | Implementation | Evidence |
|---|---|---|
| Late actor, both `/change person dev late_by 40` and `available 15:40`; hold all early Dev scenes, retain feasible work | `coordinator/change_values.py:18`, `coordinator/planning.py:30`, `coordinator/workflow_models.py:134` | `test_late_actor_holds_every_early_scene_and_preserves_later_work`; authority matrix `test_authority_and_impostor`; real r3, fixtures `day/09-...` through `day/13-...` |
| Kit failure; confirmed reviewed lav alternative; missing/unknown kit cannot pass | `coordinator/commands.py:25`, `coordinator/checker.py:116`, `coordinator/constraints.py:82`, `fixtures/film/constraints-r1.yaml:58` | `test_kit_shorthand_normalizes_to_authority_checked_status`, `test_kit_replacement_requires_reviewed_alternative_and_confirmation`, authority matrix; real r4. Both the requested four-token kit shorthand and explicit `status unavailable` work |
| Losing light and permission windows; interiors remain usable | `coordinator/checker.py:93`, `coordinator/change_values.py:51`, `coordinator/constraints.py:68` | `test_light_and_window_rules_keep_interiors_usable`, `test_light_change_runs_delegate_check_decide_release_and_confirm`, authority matrix; separate `uv run python -m scripts.demo_day --light-only` real-loop r2 with eight HTTP snapshots in `fixtures/ui-state/light/` |
| New overrun fact, total observed extension, downstream travel/hard-stop/window/light checks | `coordinator/constraints.py:84`, `coordinator/change_values.py:26`, `coordinator/checker.py:108`, `coordinator/ripple.py:12` | `test_overrun_ripples_without_touching_distant_scene_and_cannot_shrink`, `test_overrun_checks_hard_stop_window_light_and_travel`, replay/restart test; real r5 |
| Correct named authority for every change | `coordinator/runtime.py:133`, `coordinator/workflow_models.py:149`, `coordinator/config.py:19` | Eight cases in `test_authority_and_impostor`, each first rejecting an impostor without mutating facts. AD handles arrivals; producer handles location facts; AD/camera handles kit; AD/human Script Supervisor handles overrun |
| Only held scenes are replaced; stale questions close and combined scope survives | `coordinator/planning.py:30`, `coordinator/loop.py:154`, `coordinator/loop.py:254` | `test_new_change_closes_question_and_replans_union`, `test_held_scope_cannot_touch_valid_scene`, `test_ripple_uses_adjacent_travel_not_a_skipped_route`; real r3/r5 preserve Scene 3 |
| Moved scenes show old → new times; exact changed-call audience | `coordinator/render_props.py:27`, `coordinator/render_props.py:72`, `coordinator/release.py:63` | Overrun test checks old/new scene and Maya call text. `test_equal_call_instants_do_not_force_confirmation_for_offset_spelling`; `uv run python -m work.W6-verify` independently checks every release audience |
| Four-beat real day, reset twice with matching normalized outcomes | `scripts/demo_day.py:62`, `scripts/day_workers.py:20` | Four successful normal resets; runs 1, 2, 3 and 4 reach r5. `data/w6-normalized-1.json`, `data/w6-normalized-2.json`, `data/w6-normalized-4.json` compare equal. Final current-run chat receipt checks: `data/w6-run-4.log`. The separate light run is `data/w6-light.log` |
| Real `/api/state` fixtures at every required beat, existing fixtures untouched | `scripts/demo_day.py:130`, `fixtures/ui-state/day/01-initial-decision.json:1`, `fixtures/ui-state/day/23-r5-confirmed.json:1` | 23 day snapshots plus eight light snapshots. Record and hold are atomic, so those two beats may have identical state. `uv run python work/W6-audit.py` verifies original `0N-*.json` byte-for-byte |
| UI contract and review server | `docs/UI-CONTRACT.md:103`, `scripts/serve_demo.py:13`, `work/W6-verify.py:16` | `uv run python -m scripts.serve_demo --settings data/w6-demo/settings.json`; server **http://127.0.0.1:8787**, Python PID **42416**, managed session 38756. Page/API/final PNG/MP4 return 200. `data/w6-verification.json`; saved public state `work/W6-state.json:1` |

Every day change follows record → hold → delegated Supervisor → delegated AD → deterministic check → native director decision → release → confirmations. Simulated workers send proposals through real Switch roles; simulated people post/answer through real Mattermost. The harness never invokes coordinator transitions directly. The normal day produces r1–r5; every release is a complete snapshot.

| Release | Changed calls requiring fresh confirmation | Confirmed |
|---|---|---|
| r1 | Maya, Dev, Leela | All three |
| r2, lost rooftop | None | None required; existing duties carry forward |
| r3, late Dev | Maya, Dev, Leela | All three |
| r4, recorder failure | None | None required; existing duties carry forward |
| r5, Scene 1 overrun | Maya only | Maya |

`late_by` uses the released setup-inclusive call. In the real day Dev's original call is 14:45, so 40 minutes late means available from 15:25, with Scene 1 photography moving to 15:40 after setup. In the no-setup unit fixture, the same command means 15:40. Overrun is a monotonic total against the original observed end; replay never repeatedly adds 25 minutes. Existing buffer absorbs part of downstream delay; travel and setup still constrain the result.

Additional self-review fixes: confirmations are refused while scenes remain unresolved (`coordinator/loop.py:411`); unauthorized native answers get at most one replacement within the original expiry (`coordinator/loop.py:353`); equal instants in different timezone spellings do not force a new confirmation. The older `scripts/demo_dry_run.py:210` confirmation wait now follows `acks.expected`, preserving its entrypoint under W6's narrower policy; that older full rehearsal was not separately rerun in W6.

No git commands or commits, global installs, Chrome, edits to Switch, or W6-authored edits to `ui/`, `render/`, or `agents/`. Credentials and ledgers remain under ignored `data/` and `.env` files. No files were deleted and no pre-existing process was stopped. Port 8787 was free when W6 started its review server. Authored files use LF and stay below 500 lines; public fixtures are compact JSON. A concurrent renderer-staging change in `scripts/prepare_renderer.py:16` appeared during W6; it is preserved and is not W6-authored. Filesystem-only comparison: `data/w6-diff.txt`; audit: `data/w6-audit.json`.

## 2. Runtime facts learned

- Real Switch is on **127.0.0.1:8000**, Mattermost on **127.0.0.1:8065**, rehearsal API on **127.0.0.1:8789**, and final review API on **127.0.0.1:8787**.
- **Source wins:** native questions use Switch's `/agent-sessions/{session_id}/approvals` payload with `request_id`, `turn_id`, `kind: questions`, `questions`, `options: []`, explicit room and aware expiry (`core/switch_core/bridges/agent/api/activity_routes.py:231`). Answers are also relayed as room text (`core/switch_core/bridges/collaboration/collaboration_core.py:1958`). There is no extra consumed-answer flag. W6 reuses W5's real client/parser.
- The first setup attempt hit the exact sanitized error **`Switch request refused (HTTP 404)`** when the new identity tried to close a W5-owned question. The local client's `question_path` is always its identity-directory sibling `questions.json` (`coordinator/switch_client.py:74`). W6 now keeps identities, cache and ledger in `data/w6-demo`; it does not share W5's question cache. The rehearsal helper now accepts an explicit identity directory (`scripts/demo_switch.py:152`).
- Identity lookup is receipt-matched room history, not an assumed agent self-echo. Workers and people retain distinct authenticated transport identities.
- **No Discord bridge is configured.** These are real Switch/Mattermost posts in private `w6-production`, displayed as `#production`. Publication means accepted by Switch for relay; it does not prove Discord delivery, crew-account media playback, or production/crew separation on Discord. The successful HTTP PNG/MP4 checks prove the review server serves real media bytes.
- No new server protocol difference beyond the established W4/W5 findings was observed. Heartbeat source remains 10-second ping / 30-second TTL (`.../protocol/liveness.py:25`).

## 3. Needs the human

For this W6 review, no new account, token or setup click is needed:

1. Open **http://127.0.0.1:8787** in Edge. Inspect r5, the held/replanned scene history, Maya's changed call and confirmation. Replay files are in `fixtures/ui-state/day/`.
2. Claude reviews `data/w6-diff.txt`, the changed files and this report, then commits. No new Claude review was provided during this turn, so there was no Claude review available for me to review back.
3. The UI owner adds `location.light_until` and `scene.overrun` to the report form's field list (`ui/src/components/Shell.tsx:193`), using `docs/UI-CONTRACT.md:103`. This brief forbids W6 edits to `ui/`; authenticated chat commands already work.

For the actual shoot:

1. Connect the two real Console workers, claim their separate roles and allow coordinator addressing. Replace simulated identities with the reviewed authenticated director, producer, AD, camera/kit authority and optional human Script Supervisor in ignored configuration. `TAKE_TWO_SCRIPT_SUPERVISOR_ID` is a human authority, distinct from the worker sender.
2. Confirm the actual lav exists and is permitted for the dialogue. The fixture declares it confirmed for this supplied demo; it is not evidence about physical kit on your shoot. W6 implements that reviewed replacement path; silent coverage remains rejected when sync sound is required.
3. Connect Discord, link the owner's identity, configure crew usernames and channel/file permissions, then verify PNG opening and MP4 playback from a crew account. Use the intended production ledger/configuration; the W6 review is an isolated rehearsal.
4. Before rerunning `demo_day`, stop the W6 review process shown above. Never reset a ledger while its coordinator is serving. Each script reset backs up the offline ledger and leaves room history and credentials intact.

## 4. Found, not fixed

- **Read-only UI fields:** `ui/src/components/Shell.tsx:193` still omits `light_until` and `overrun`; add the two documented options. No UI edit was made by W6.
- **Question-cache lifecycle:** `coordinator/switch_client.py:74`, `coordinator/switch_client.py:282` still share a sibling cache within one directory and grow across settled decisions. W6 isolates its directory and its reset helper refuses histories above 50 (`scripts/demo_switch.py:241`), but general archival remains needed. Suggested fix: per-identity bounded cache with settled payloads archived while retaining durable dedupe. W4 F18's unauthorized-reissue portion is fixed; its cache portion is not.
- **Uncertain publications and media reply roots:** W4 F9/F11 remain at `coordinator/dispatcher.py:306` and `coordinator/dispatcher.py:374`. Add authenticated reconciliation/resolution and persist media/thread receipts before enabling retries. W6 never blindly retries uncertain media.
- **Legacy ledgers retain their saved constraints:** `coordinator/loop.py:59`. The supplied W6 fixture's exterior flags and confirmed lav alternatives seed fresh ledgers; old saved constraints are not silently overwritten. Review/migrate facts explicitly, or use the backed-up isolated reset harness before a demo.
- **Preview timing:** `coordinator/loop.py:267` still renders non-initial candidates, including logistics, through the inherited path. The real day passes with the existing renderer; adding a separately reviewed logistics-only preview bypass remains outside this change.

## 5. Self-review

I re-read the complete authored source diff and new tests, inspected the real HTTP snapshots and verbatim chat evidence, and checked the filesystem audit. Five break attempts:

1. Spoofed each authority, sent negative/fractional/oversized delay values and malformed times. Facts and revisions stay unchanged; a visible response is queued. Tried the exact four-token kit shorthand as well as canonical status commands.
2. Dropped sound entirely, substituted unknown kit, omitted exterior-light flags, and extended an overrun through a hard stop, location window, light cutoff and insufficient travel. The deterministic checker rejects or requires verification; only a confirmed reviewed replacement passes.
3. Replayed an overrun command and its outcome across coordinator restarts. The total remains 25 minutes, one release is committed, answered requests stay answered, and no decision reopens.
4. Changed availability while a question was open, tried its stale answer, proposed moving an unaffected valid scene, and confirmed an old plan during a hold. The question closes outdated, the held union survives, no stale release/confirmation succeeds, and out-of-scope worker replies get one retry then visible failure.
5. Repeated unauthorized answers, used a non-adjacent long travel route, and spelled one call in UTC and IST. Only one replacement card is issued within the original deadline; adjacent travel avoids unnecessary holds; equal instants do not create false affected people. Independent HTTP verification checks all five exact confirmation audiences.

Must-never audit: (1) checked current revisions and held-scene scope gate candidate approval/publication; (2) SQLite dedupe, total overrun and transactional outbox survive replay/restart; (3) named identities gate changes and releases; (4) existing expiry tests still prove silence chooses nothing; (5) new refusals/validation failures have timeline items and visible messages; (6) new minutes, alternatives, jobs, frames, waits and unauthorized reissues are bounded, with the pre-existing general cache-archival limitation explicitly above; (7) malformed agent text still gets one retry then visible failure in the full suite. No claim is made that the inherited uncertain-publication or cache-archival findings are solved.

## Exact observed HOLD and release texts

Day strings were read back from Mattermost in the current run after filtering out earlier-reset posts (`data/w6-demo/chat.json`). Light strings were read back during the separate real-loop light rehearsal (`data/w6-demo/chat-light.json`).

### rooftop

HOLD:

```text
HOLD · Scene 3 (The confession). Rooftop permission refused. Do not go to the rooftop.
Scenes 1 and 2 are unchanged. An update is coming.
```

Release:

```text
TAKE TWO · Release 2 (blue pages) · The Last Light, Day 1
What changed: Scene 3 moves to the stairwell, 16:45–18:00.
Scene 3 moved: 16:45–18:15 → 16:45–18:00.
Sc 1 · The missed call · INT. STAIRWELL · 15:00–15:15
Sc 2 · A promise · EXT. COURTYARD · 15:25–15:35
Sc 3* · The confession · INT. STAIRWELL · 16:45–18:00
Call times: Maya 15:25 · Dev 14:45 · Leela 14:45   (* = changed)
Re-confirm changed calls: none; existing confirmations carry forward.
Sc 1 coverage: wide, two-shot, close-up; kit: sound_recorder; setup 15m; wrap 0m.
Sc 2 coverage: wide, two-shot, close-up; kit: sound_recorder; setup 0m; wrap 0m.
Sc 3 coverage: wide, two-shot, close-up; kit: sound_recorder; setup 15m; wrap 0m.
Reply "confirm r2". Replies about release 1 will be corrected.
```

### late-actor

HOLD:

```text
HOLD · Scene 1 (The missed call), Scene 2 (A promise). Dev late_by 40.
Scenes 3 are unchanged. An update is coming.
```

Release:

```text
TAKE TWO · Release 3 (pink pages) · The Last Light, Day 1
What changed: Wait for Dev, move early scenes.
Scene 1 moved: 15:00–15:15 → 15:40–15:55.
Scene 2 moved: 15:25–15:35 → 16:05–16:15.
Sc 1* · The missed call · INT. STAIRWELL · 15:40–15:55
Sc 2* · A promise · EXT. COURTYARD · 16:05–16:15
Sc 3 · The confession · INT. STAIRWELL · 16:45–18:00
Call times: Maya 16:05 · Dev 15:25 · Leela 15:25   (* = changed)
Re-confirm changed calls: Maya 15:25 → 16:05; Dev 14:45 → 15:25; Leela 14:45 → 15:25.
Sc 1 coverage: wide, two-shot, close-up; kit: sound_recorder; setup 15m; wrap 0m.
Sc 2 coverage: wide, two-shot, close-up; kit: sound_recorder; setup 0m; wrap 0m.
Sc 3 coverage: wide, two-shot, close-up; kit: sound_recorder; setup 15m; wrap 0m.
Reply "confirm r3". Replies about release 2 will be corrected.
```

### kit-failure

HOLD:

```text
HOLD · Scene 1 (The missed call), Scene 2 (A promise), Scene 3 (The confession). Sound_recorder status unavailable. An update is coming.
```

Release:

```text
TAKE TWO · Release 4 (yellow pages) · The Last Light, Day 1
What changed: Use the confirmed lav, keep every call.
Sc 1* · The missed call · INT. STAIRWELL · 15:40–15:55
Sc 2* · A promise · EXT. COURTYARD · 16:05–16:15
Sc 3* · The confession · INT. STAIRWELL · 16:45–18:00
Call times: Maya 16:05 · Dev 15:25 · Leela 15:25   (* = changed)
Re-confirm changed calls: none; existing confirmations carry forward.
Sc 1 coverage: wide, two-shot, close-up; kit: lav; setup 15m; wrap 0m.
Sc 2 coverage: wide, two-shot, close-up; kit: lav; setup 0m; wrap 0m.
Sc 3 coverage: wide, two-shot, close-up; kit: lav; setup 15m; wrap 0m.
Reply "confirm r4". Replies about release 3 will be corrected.
```

### overrun

HOLD:

```text
HOLD · Scene 1 (The missed call), Scene 2 (A promise). S1 overrun 25.
Scenes 3 are unchanged. An update is coming.
```

Release:

```text
TAKE TWO · Release 5 (green pages) · The Last Light, Day 1
What changed: Record the overrun, move the promise.
Scene 1 moved: 15:40–15:55 → 15:40–16:20.
Scene 2 moved: 16:05–16:15 → 16:20–16:30.
Sc 1* · The missed call · INT. STAIRWELL · 15:40–16:20
Sc 2* · A promise · EXT. COURTYARD · 16:20–16:30
Sc 3 · The confession · INT. STAIRWELL · 16:45–18:00
Call times: Maya 16:20 · Dev 15:25 · Leela 15:25   (* = changed)
Re-confirm changed calls: Maya 16:05 → 16:20.
Sc 1 coverage: wide, two-shot, close-up; kit: lav; setup 15m; wrap 0m.
Sc 2 coverage: wide, two-shot, close-up; kit: lav; setup 0m; wrap 0m.
Sc 3 coverage: wide, two-shot, close-up; kit: lav; setup 15m; wrap 0m.
Reply "confirm r5". Replies about release 4 will be corrected.
```

### losing-light

HOLD:

```text
HOLD · Scene 3 (The confession). Rooftop light_until 17:20.
Scenes 1 and 2 are unchanged. An update is coming.
```

Release:

```text
TAKE TWO · Release 2 (blue pages) · The Last Light, Day 1
What changed: Scene 3 moves to the stairwell, 16:45–18:00.
Scene 3 moved: 16:45–18:15 → 16:45–18:00.
Sc 1 · The missed call · INT. STAIRWELL · 15:00–15:15
Sc 2 · A promise · EXT. COURTYARD · 15:25–15:35
Sc 3* · The confession · INT. STAIRWELL · 16:45–18:00
Call times: Maya 15:25 · Dev 14:45 · Leela 14:45   (* = changed)
Re-confirm changed calls: none; existing confirmations carry forward.
Sc 1 coverage: wide, two-shot, close-up; kit: sound_recorder; setup 15m; wrap 0m.
Sc 2 coverage: wide, two-shot, close-up; kit: sound_recorder; setup 0m; wrap 0m.
Sc 3 coverage: wide, two-shot, close-up; kit: sound_recorder; setup 15m; wrap 0m.
Reply "confirm r2". Replies about release 1 will be corrected.
```
