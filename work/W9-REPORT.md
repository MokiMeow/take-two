# W9 report

## 1. Done

| Acceptance | Files | Proof |
|---|---|---|
| Record resolves and links its source report; Ignore resolves without changing facts | `coordinator/ui_models.py:85`, `coordinator/reports.py:172`, `coordinator/reports.py:183`, `docs/UI-CONTRACT.md:55` | `test_report_record_card_uses_authority_change_path_once_across_restart`, `test_ignore_and_wrong_authority_never_record`, `test_cannot_report_resolves_only_through_authority_record` |
| Human card text and personal differences; unchanged calls omitted | `coordinator/duties.py:24`, `coordinator/presentation.py:28`, `coordinator/loop.py:283`, `fixtures/film/crew.yaml:4` | `test_first_release_uses_human_labels_and_no_empty_or_previous_call`, `test_location_same_call_needs_all_scene_people`, `test_kit_change_only_sound_owner_needs_confirmation` |
| Deterministic catch-up deadline tests | `coordinator/tests/test_w5_boundaries.py:88` | Both `test_catchup_outcome_fetch_cannot_overrun_deadline` and `test_catchup_outcome_processing_cannot_overrun_deadline` use a controlled clock/timer; no millisecond wait or production test hook |
| Full suite green twice consecutively | `coordinator/tests/` | `uv run pytest -q`: **320 passed, 1 skipped, 1 warning** in each of `data/w9-tests-final-2.txt` and `data/w9-tests-final-3.txt` |
| Real Switch day re-recorded; original examples preserved | `scripts/demo_day.py:172`, `scripts/demo_day.py:210`, `fixtures/ui-state/day/07-maya-change-confirmed.json:1`, `fixtures/ui-state/day/12-late-actor-recorded.json:1` | `uv run python -m scripts.demo_day`: r5, 26 beats; `work/W9-real-switch.log`. `uv run python work/W9-verify.py` validates all 26 snapshots, report links, wording and six unchanged top-level fixture hashes |
| Review server on 8787 with current UI | `scripts/serve_demo.py:13`, `work/W9-browser.mjs:14` | `node work/W9-browser.mjs`: headless Edge visits live state and all 26 moments; pending card present at 11, absent at 7/12/26, no page errors. `/`, state, PNG and MP4 return HTTP 200 |

Original reports keep `status: pending_confirmation` for audit; resolution determines whether they still await action. Recorded facts keep their existing status semantics. Both Maya and Dev now have `resolution: recorded`, `resolved_by_change` and `resolved_at`. Ignored reports use `ignored`; legacy `dismissed` remains readable. No automatic report matching or supersession was added.

Before / after examples from personal and authority cards:

| Before | After |
|---|---|
| `Scene 1: kit sound_recorder → lav` | `Scene 1: kit sound recorder → lav mic` |
| `camera_sound; kit sound_recorder` | `Camera / sound; kit sound recorder` |
| `actor; kit none` | `Actor` |
| `Scene 3: rooftop → stairwell` | `Scene 3: Rooftop → Stairwell` |
| `Call 14:45 (was 14:45)` | omitted |
| `Call 15:25 (was unconfirmed)` | `Call 15:25` |
| `Record person maya hard_stop 18:00?` | `Record Maya: hard stop 18:00?` |

The first focused regression run failed on the missing links/old wording, then passed. The first full suite failed `test_w4_chatter_never_becomes_report_but_maya_does_once` and `test_known_authority_report_uses_configured_name_not_message_name` on old lowercase-role expectations; those were updated. Browser verification caught beat 11 being captured before Dev's report committed; the driver now waits for its exact report ID and the day was re-recorded. Old normalized baselines were archived under `data/w9-before/`, so the changed replay deliberately establishes a new baseline (`normalized_match: false`), not a reproducibility claim.

## 2. Runtime facts learned

Real Switch `/health` on **8000** and Mattermost `/api/v4/system/ping` on **8065** returned 200. Driver API used **8789**; review uses **8787**. People/workers are simulated, transport/cards/media are real Switch/Mattermost. No Discord bridge is configured; external Discord delivery is unverified.

No new Switch API disagreement was found. **Source wins:** `E:/DevDrive/switch/core/switch_core/session_activity/service.py:465` checks addressing permission and settles the first accepted answer; Take Two still checks the named authority itself. Licence checked: Apache 2.0 with modified Commons Clause. Inspection also found W8 already wrote `resolution: recorded`; W9 supplies the missing link/time and the requested Ignore vocabulary.

The existing `ui/dist` was stale. The current UI was built directly into `data/w9-ui-dist` using `node ui/node_modules/vite/bin/vite.js build ui --config ui/vite.config.ts --configLoader native --outDir ../data/w9-ui-dist`. Build passed with the existing large-chunk warning. The review server uses `--ui-dist data/w9-ui-dist` (PID **41756**). No UI source/output directory was written.

## 3. Needs the human

1. Open **http://127.0.0.1:8787/** in Edge for live r5, or **http://127.0.0.1:8787/?fixtures=day** for the recorded day. No new account, token or setup click is needed.
2. Review this diff/report; Claude owns the commit and subsequent review. No Claude review has yet been supplied for me to respond to.

## 4. Found, not fixed

- `coordinator/api.py:173` still defaults normal launches to the older `ui/dist`. The UI owner should rebuild that directory before a normal deployment; W9's review uses the fresh build under `data/`.
- `coordinator/rooms.py:24`: no configured Discord bridge. Follow `docs/SETUP-HUMAN.md` and verify media from a real crew account before claiming Discord delivery.
- Existing skip: `coordinator/tests/test_api.py:110` needs Windows symlink privilege. Existing warning: `.venv/Lib/site-packages/starlette/testclient.py:51` uses a deprecated AnyIO alias. Neither was hidden.

## 5. Self-review

Re-read all authored source/test/script changes with filesystem comparisons (`data/w9-diff.txt`) and checked the recorded snapshots. Five break attempts:

1. Replay Record after restart: no second revision/change; original resolution/link/time retained.
2. Answer as the wrong authority, then Ignore: no unauthorized fact; Ignore resolves only the source report.
3. Submit Can't make it and a report without a usable proposal: only the authorized Record resolves the former; unrelated changes leave the latter pending.
4. Keep calls identical while moving a location or replacing kit: no false call change; affected audiences and personal confirmation baselines remain correct.
5. Expire during outcome fetch/processing using the controlled timer; replay the real day under load: recovery stays paused with a visible error, and the driver waits for committed reports before capture.

Invariant audit: (1) approval/revision checks retained; (2) resolution/fact/outcome share the existing durable transaction and dedupe; (3) named authority still required; (4) expiry never selects; (5) failure timeline/outbox behavior retained; (6) existing bounds/backoff retained, new report wait capped at 30 seconds; (7) strict extraction schema and one-retry bad-JSON handling retained. Browser and fixture checks passed. No git commands, global installs, Switch edits, or edits under `ui/`, `render/`, `agents/`; no unrelated files deleted or processes stopped. Authored text is LF and under 500 lines.
