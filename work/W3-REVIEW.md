# W3 hostile review

**Verdict: not ready to build on or rehearse end to end.** The existing tests pass, but the real worker format is rejected, renderer inputs are incompatible, and reconnect recovery has no catch-up barrier protecting publication. Configuration alone cannot complete FLOW.

The five most important findings:

1. **Blocker — F1:** the agents' instructed fenced, addressed replies fail `json.loads`; the Supervisor-to-AD handoff stops.
2. **Blocker — F2:** render props are never constructed. Previews can inherit fictional demo labels and hashes; call sheets encounter incompatible scene rows.
3. **Blocker — F3:** restart/reconnect enables effects before missed changes are drained; an owed answer can be processed against stale facts.
4. **Major — F4:** there is no initial three-scene schedule approval/release or automatic shoot-day provisioning path. Per-scene planning produces different release numbers and approval semantics.
5. **Major — F5:** a newer change discards the previous unresolved work; affected scenes come only from old published plans. Maya's hard stop also unnecessarily holds Scene 2, which selecting Scene 3 never restores.

## Evidence and review boundaries

Read README, all seven requested specification/review documents, `tasks/WORKER-STANDARD.md`, W1's complete report, coordinator implementation/tests, scripts/templates/film fixtures, renderer schemas/components/CLI, and the relevant Switch server implementation. Switch source was read only. No git commands, Switch calls, POSTs, browser launches, installations, or process stops were performed.

Permitted verification:

```powershell
$env:UV_CACHE_DIR='data/uv-cache'
$env:PYTHONDONTWRITEBYTECODE='1'
uv run pytest --basetemp=data/pytest-w3 -p no:cacheprovider
```

Result: **190 passed, 1 skipped, 1 warning**, Python 3.12.10, 25.89 seconds. The skip is the Windows symlink test (`coordinator/tests/test_api.py:102`); the warning is Starlette's deprecated AnyIO alias. No new tests or reproduction programs were written. Findings below are source traces, not claims of executed external scenarios. The suite principally exercises separate components: `test_loop.py:17` begins with a fictional published r1; `test_dispatcher.py:15` substitutes a production object and `:31` substitutes a renderer. Passing those tests does not prove their real integration.

GET `http://127.0.0.1:8787/api/state` returned **200**. Observed: revisions 1/1, three held scenes with no plans, no jobs/releases, null decision, three pending Control Room smoke reports, and two generic `message failed` timeline entries. This confirms an honest uninitialized schedule; it does not demonstrate the normal-day FLOW or Switch/Discord delivery. No credentials were read or printed.

Review acceptance coverage:

| Requested review | Evidence/result |
|---|---|
| Spec, 16 prior fixes, seven invariants | Findings F1–F20 and invariant audit below. Prior fixes 1/6/14/15 are incomplete at integration/initialization; 8/9/10 at worker/checker inputs; 11/12 at replay/publication recovery; 4/13 at holds/confirmations; 16 remains an evidence-label concern. Source-supported protocol primitives in fixes 2/3/5/7 are present. |
| Every Switch client call | Route/payload audit below; no invented attachment operation or wrong endpoint found. Runtime ordering and delivery interpretation remain defective. |
| Exact FLOW story | Step-by-step trace at the end, including its first break. |
| Compare Claude's review | C1–C7 comparison below, with a correction to its renderer failure claim. |

## Findings — all found, not fixed

### F1 — blocker — Worker instructions and parser disagree

**Location:** `coordinator/loop.py:204`, `coordinator/runtime.py:252`; `agents/script-supervisor.md:19`, `agents/first-ad.md:16`.

**What breaks / scenario:** both role instructions require one fenced JSON block addressed to the coordinator. A reply consisting only of that fenced block already fails whole-body `json.loads`. Switch's own `send_targeted_message` additionally prepends `@take-two-coordinator ` (`E:/DevDrive/switch/core/switch_core/bridges/agent/protocol/agent_core.py:2137`); room event construction preserves the body (`protocol/event_buffer.py:1599`). The authorized Supervisor follows its instructions, receives one retry, then fails. The AD is never requested. Existing loop tests supply dictionaries or naked JSON and miss this.

**Exact fix:** define one bounded wire format shared by role instructions and parser. Extract a single JSON object from the explicitly allowed mention/fence envelope, reject multiple blocks/objects and trailing substantive text, then run the existing Pydantic validation and identity/revision checks. Test actual mention-plus-fence messages for both roles. Do not let extraction bypass job binding.

### F2 — blocker — Render data is incompatible; defaults can masquerade as candidate facts

**Location:** `coordinator/dispatcher.py:142`, `:199`; `coordinator/render_bridge.py:32`; `render/src/schema.ts:5`, `:21`; `render/src/Root.tsx:21`.

**What breaks / scenario:** preview dispatch passes only the scheduling manifest; call-sheet dispatch passes only `{scenes: [...]}`. The bridge removes `manifest_hash` before writing input JSON. There is no adapter to the renderer's actual schemas. Field mismatches are:

| Output | Missing / incompatible fields |
|---|---|
| Preview required metadata | `letter`, `label`, `scene_number`, `scene_title` are absent. The queued preview payload even omits candidate label and story cost (`loop.py:257`). |
| Preview identity | Required `manifest_hash` is absent: not in the stored manifest and explicitly stripped by the bridge. |
| Preview people | Coordinator sends `string[]`; renderer expects `{id, name}[]`. |
| Preview bounds | Manifest permits 100 shots, 200 people, and 200-character IDs; renderer permits 6 shots of at most 30 characters, 4 people, and a location of at most 40 characters. Candidate label permits 200 characters versus renderer 80. |
| Preview optional overrides | `sunset` and `crowd` have no coordinator representation. Location-derived art defaults are used; these overrides cannot be expressed. |
| Preview extra fields | `scene_id`, setup/wrap, capabilities, source revisions and `requires_light` are scheduling fields, not renderer props. They do not supply the missing metadata. |
| Call-sheet production | Entire required `production {title, day, date, timezone}` is absent. Coordinator production has no separate formatted `date` field. |
| Call-sheet release | Entire required `release {number, release_id, manifest_hash, summary, changes, created_at}` is absent. No release identity reaches this render. |
| Call-sheet top level | Required `general_call`, `crew`, `locations`, `confirm_hint` are absent; optional `sunset` is absent. Crew rows need names, roles, call times and optional changed flags; location rows need names and optional notes. |
| Call-sheet scene rows | Need `number`, `title`, `location`, `start`, `end`, `cast`, optional `changed`. Supplied active rows instead carry `scene_id`, people IDs and scheduling fields: number/title/cast/changed are missing. Held rows have only scene ID, validity and reason, with no executable location/times; the schema has no hold-row representation. `unchanged` is not `changed`. |
| Call-sheet bounds | Coordinator allows 200 scenes/500 crew/200 locations; renderer allows 12/20/6. |
| File bound | Python accepts 256 KiB input; renderer CLI accepts 64 KiB (`render/cli.mjs:14`). |

Do not assume the Zod registration makes all bad inputs fail. The CLI does not call either schema's `parse`; local Remotion source merges composition `defaultProps` with input props (`render/node_modules/remotion/dist/cjs/ResolveCompositionConfig.js:77`). Thus both passing previews can inherit **A / Stairwell, reduced coverage**, default scene metadata and a sample hash; string people have no `.name`. Such an MP4 can pass the bridge's scheduling-hash check and be marked ready. Call-sheet scenes replace the default array but lack `cast`; `render/src/CallSheet.tsx:63` calls `s.cast.join`, causing failure and text fallback. These are source-derived consequences; no renderer/browser was launched in W3.

**Exact fix:** add explicit validated preview/call-sheet prop builders from the immutable candidate/release snapshot plus trusted script/crew metadata. Keep canonical manifest hashing separate from serialized presentation props; pass the actual hash into the props. Validate complete raw props before defaults can fill missing business data. Give held scenes a truthful schema/rendering representation. Align size/count limits and test production-generated props against both schemas, including park versus stairwell labels and the actual r2 stamp.

### F3 — blocker — Publication resumes before replay has reconciled missed changes

**Location:** `coordinator/runtime.py:164`, `:175`, `:177`, `:198`; `coordinator/switch_client.py:351`.

**What breaks / scenario:** while the coordinator is down, the Producer refuses a candidate's location and the director answers the older card. On reconnection `connected()` fetches and applies owed outcomes against the old local constraints, then sets `ready=True`. Missed room messages have not been explicitly drained. Switch yields connection state before catch-up (`protocol/stream.py:259`) and can yield outcomes before room events (`:304`). The service task can dispatch the resulting release while replay is still arriving. During a transient socket disconnect, `ready` also remains true throughout reconnect backoff; only a later opening frame or terminal exception changes it. A `room_released` control frame is ignored (`runtime.py:247`).

**Exact fix:** pause effects as soon as transport health/room ownership is lost. Establish a durable replay fence using authoritative source positions/history, drain through it, and apply missed changes before outcomes/publication. A connection-state frame is a starting baseline, not proof of catch-up. Handle `room_released` as loss of the relevant room context. Add an integrated Runtime/Loop/Dispatcher test with an owed answer, an offline refusal and delayed replay; assert zero stale crew sends.

### F4 — major — Initial r1 and shoot-day provisioning are missing application paths

**Location:** `coordinator/runtime.py:90`, `coordinator/workflow_models.py:30`, `coordinator/loop.py:368`; `coordinator/switch_client.py:242`.

**What breaks / scenario:** live startup correctly creates no approved plans. However, a Proposal contains exactly one `Manifest`, and `_release` replaces exactly one scene. Three AD scene manifests become competing choices, not a single checked three-scene schedule approved with one card. Following W1's workaround of approving each scene separately creates r1/r2/r3 before the rooftop change, so the replacement is not FLOW's r2. Runtime never calls `create_room_from_yaml` for the day, persists no day-room mapping and creates no day documents; only the probe provisions production. Supplying the renderer, workers and bridge does not implement these steps.

The example r1 also needs a data repair: its s2-to-rooftop transition has no `courtyard->rooftop` travel fact (`fixtures/film/constraints-r1.yaml:41`), so checking that initial schedule would require verification rather than silently passing.

**Exact fix:** implement an authenticated initial-planning transition with one candidate containing the complete schedule, cross-scene checks, one approval and one r1 commit. Provision/reconcile the shoot-day room from the existing template, persist its identity, inspect attachment failures, and create coordinator-owned day documents. Supply the missing verified travel fact. Keep fixture approvals out of the live ledger.

### F5 — major — New changes lose unresolved scene scope and over-hold unaffected scenes

**Location:** `coordinator/loop.py:105`, `:140`, `:150`, `:230`, `:436`.

**What breaks / scenario:** `_invalidate` clears all pending candidates/jobs, then `_affected` consults only `scene.plan`. With rooftop r1 still stored and a stairwell candidate pending, a confirmed refusal of stairwell cancels the question but produces `scene_ids=[]`; every replacement candidate is rejected as the wrong scene. An unrelated change to s1 similarly abandons the unresolved s3 change. Conversely Maya's 18:00 hard stop holds both s2 and s3 merely because she is listed, although s2 finishes at 15:35. Choosing s3 restores only s3, leaving s2 held in release 2. A safety hold anywhere also blocks every release through the global holds predicate (`:340`, `:412`).

**Exact fix:** maintain a durable unresolved-scene set across changes; include current plans, pending candidate dependencies and active holds. Recheck current manifests to determine which plans actually become invalid rather than holding every reference unconditionally. Delegate/release a coherent plan for all unresolved scenes, and scope safety clearance to the instructions being made usable while preserving unrelated holds in the snapshot.

### F6 — major — The checker trusts the worker to declare every required person/capability

**Location:** `coordinator/checker.py:72`, `:99`, `:106`; `coordinator/runtime.py:29`; `coordinator/loop.py:239`.

**What breaks / scenario:** required script cast/props are discarded by `ScriptScene`; constraints contain no required cast or capability set. An s3 candidate with only Dev and `capabilities=[]` can pass: Maya's hard stop and the sound recorder are never checked because they were omitted. Story verification is keyed only by scene and location, so it still says the confession is confirmed for that location. Supervisor `must_keep` is passed to the AD but never added to checked requirements; a newly identified hard rule can disappear from feasibility entirely.

**Exact fix:** keep reviewed cast and required capabilities in trusted scene requirements; validate candidate membership and capability completeness independently of its declarations. Bind approved/verified Supervisor requirements to the relevant revision; new unverified rules must require human verification. Do not let a proposal remove checks by dropping resources or setting `requires_light=False` for a shot whose trusted requirements demand light.

### F7 — major — Director's native decision has no previews or manifest details

**Location:** `coordinator/dispatcher.py:195`; `coordinator/loop.py:269`.

**What breaks / scenario:** successful previews are stored only as local `/media/...` URLs. The dispatcher never uploads them to production. The Switch question contains labels/story-cost text only, with no preview URLs, time/cast details or hash. A director answering the promised Mattermost card cannot inspect the two sketches there. Control Room displays cannot substitute for the specified production-room presentation without an explicit product change.

**Exact fix:** publish bound preview attachments and concise checked manifest summaries to production before opening the card, record their receipts, and reference the corresponding options in that card. Fall back visibly to text when a render fails. Recheck revision/hash after presentation and before opening.

### F8 — major — Timely authenticated answers can be permanently discarded after restart

**Location:** `coordinator/loop.py:299`, `:308`, `:477`; `coordinator/runtime.py:326`.

**What breaks / scenario:** director answers at 15:59, card expires at 16:00, coordinator reconnects at 16:01. Switch has durably recorded an answered outcome with `answered_at` before expiry, but the coordinator tests processing time, records the outcome as deduped, queues delivered, and discards it. The service also expires locally before its periodic outcome poll. Once local status is expired, even a valid owed answer is treated as obsolete. The direct late-outcome branch changes status without an expiry timeline item/reminder; the ticker then skips it.

**Exact fix:** reconcile authoritative outcomes before local expiry; distinguish an unanswered expired request from a timely server-recorded answer delivered late. Validate server state and answer timestamp, then recheck current revisions/authority/manifest. Commit a clear expiry/rejection reason and visible message for every terminal outcome. Never select on silence.

### F9 — major — Uncertain/failed publications have no resolution path

**Location:** `coordinator/dispatcher.py:261`, `:290`, `:343`; `coordinator/runtime.py:329`.

**What breaks / scenario:** a call-sheet upload times out. Its effect becomes uncertain, preview/text depend on it, and those effects remain blocked. `_recover` deliberately leaves media and text uncertain; no code searches delivery history, accepts operator reconciliation, or retries that logical publication. Restart repeats a notice, not recovery. HTTP errors are wrapped as `SwitchError` and classified nontransient even for 429/5xx (`switch_client.py:129`), further reducing recoverability. The stated "reconcile, then retry same release ID" never happens.

**Exact fix:** provide a bounded reconciliation workflow using stored release/file receipts and bridge history where supported, plus an explicit authenticated operator resolution when delivery cannot be established. Retry only unresolved effects with the same release ID and capped backoff; maintain downstream dependencies and per-file status. Preserve HTTP status/retryability without logging response secrets.

### F10 — major — Switch acceptance is reported as Discord publication

**Location:** `coordinator/dispatcher.py:350`, `:272`; `coordinator/loop.py:426`.

**What breaks / scenario:** final text gets a Switch event ID, so the room is marked sent and the replacement scene becomes usable once all destinations have such receipts. That event ID proves a transport-room post, not a Discord post. Switch relays outward separately (`E:/DevDrive/switch/core/switch_core/bridges/collaboration/collaboration_core.py:2498`); Discord `send_message` may return None after channel/webhook failure (`discord/adapter.py:888`, `:918`). The crew can receive no replacement while `/api/state` says published and the old release is superseded.

**Exact fix:** distinguish accepted-for-relay from verified external publication. Reconcile actual bridge delivery evidence or keep destination status uncertain until an authenticated observation confirms it. Do not infer Discord delivery from the Switch text receipt. Apply this to holds as well as releases; do not invent a delivery guarantee the server does not expose.

### F11 — major — Replies to a release's media are not correlated

**Location:** `coordinator/dispatcher.py:242`, `:353`; `coordinator/runtime.py:265`.

**What breaks / scenario:** publication media receipts are discarded; only the final text event ID is mapped to a release. Dev replies "ok see you at rooftop" in a thread rooted on the r1 call-sheet PNG or preview. With no literal r1 in his text, no mapping exists and it becomes a generic pending report instead of the required stale-plan correction. The existing test covers a text receipt or an explicit r1 mention.

**Exact fix:** validate/persist every publication receipt and map all relevant transport message/thread roots to the release, including media. Resolve reply relationships through those mappings and test both call-sheet and text-root replies.

### F12 — major — No feasible options and verification needs stop at a timeline entry

**Location:** `coordinator/loop.py:251`, `:260`, `:335`, `:340`.

**What breaks / scenario:** all candidates fail or need verification. There is no production message, no responsible-human verification request and no current candidate projection into State because `_question` is never called. The director can see an old decision or none, while the new failure reasons are trapped in workflow data. Invalid candidate answers and final-check rejection similarly record an error without a visible chat notice. This violates the explicit failure visibility and unknown-fact loop.

**Exact fix:** persist/project checked candidates independently of opening a decision. Enqueue one actionable production notice containing reasons; create a revision-bound verification request for the named fact authority. Record its confirmed change and recheck. Use the same visible terminal-failure path for failed approval checks.

### F13 — major — State fields do not consistently represent committed business progress

**Location:** `coordinator/loop.py:147`, `:164`, `:283`, `:374`; `coordinator/runtime.py:90`.

**What breaks / scenario:** normal `/change scene s3 preferences ...` updates constraints but not `state.scenes[].preferences`; the same is true for `hard`. Crew `call_time` is never assigned/recomputed, so a fixture-seeded state retains old times and a real state has none. Jobs remain queued even after successful dispatch: no running transition exists. Decision status becomes open before Switch accepts the card and stays open if opening fails. Acks always declare `affected_only` and use candidate people, ignoring configured policy/deadline; removing a previously assigned person does not mark that person affected. Unchanged people retain the old ack number without an explicit carry-forward record.

**Exact fix:** project trusted current constraints into scene fields on commit, derive duty/call-time changes from old and new complete manifests, implement queued/running and prepared/open/failed decision progress accurately, and persist configured ack policy/deadline plus explicit carry-forward records. Label platform from destination metadata rather than hard-coding Discord (`loop.py:380`). Update the UI contract for any needed progress fields.

### F14 — major — Complete releases lose manifest data and bind only the changed scene

**Location:** `coordinator/workflow_models.py:51`; `coordinator/loop.py:379`, `:436`; `coordinator/dispatcher.py:189`.

**What breaks / scenario:** after publication, the scene plan retains only location/time/setup/wrap/people. The next release reconstructs unchanged scenes from that UI projection, losing shots, capabilities and other canonical manifest fields. Its `manifest_hash` covers only the chosen replacement, not the complete snapshot being published. Text fallback omits even the chosen shots/capabilities. Thus the asserted complete plan cannot be reproduced or checked as a full canonical release, and a reduced-coverage choice is not actually described to the crew.

**Exact fix:** retain full canonical manifests per scene outside the UI projection. Commit an immutable release envelope containing that complete snapshot, its digest, the approved candidate digest and release identity. Build every artifact/text output from it; include operationally relevant shot/kit/changed-duty details. Keep presentation metadata separate from the approved creative digest.

### F15 — major — Browser reports do not follow the conservative hold pipeline

**Location:** `coordinator/runtime.py:289`; compare `coordinator/workflow_models.py:144` and `coordinator/loop.py:155`.

**What breaks / scenario:** a Control Room report of refused rooftop permission, or an explicit scene safety hold, only adds a pending row/message. It neither holds the current plan nor invalidates an open question. The same untrusted refused/unknown Switch command conservatively changes the fact to unknown and holds; anyone's structured Switch safety hold is immediate. A director can therefore approve/publish while the browser visibly contains the unresolved hazard report. The reporter string correctly grants no authority, but that does not require ignoring conservative holds.

**Exact fix:** route browser reports through an untrusted ingestion identity that cannot confirm facts or clear holds, while applying the same conservative refusal/unknown and explicit-safety hold behavior. Keep verified fact changes and all releases gated by authenticated Switch authorities. Document this distinction in the UI contract.

### F16 — major — Held obsolete plans still consume time in replacement checks

**Location:** `coordinator/workflow_models.py:67`.

**What breaks / scenario:** after a change holds s2 and s3, checking s3 still converts s2's old plan into an occupied commitment even when that plan is invalid and is supposed to be rescheduled. A feasible reorder can fail against duties that are no longer executable. Combined with the single-scene candidate model, there is no representation of moving both duties together.

**Exact fix:** check the proposed complete replacement schedule against retained executable duties and genuine external commitments. Replace all affected-scene commitments together; do not silently erase real obligations or treat held obsolete instructions as immutable external work.

### F17 — major — Boundary mismatches can quarantine valid worker replies without the promised retry

**Location:** `coordinator/runtime.py:61`, `:228`; `coordinator/constraints.py:125`, `:127`; `coordinator/ui_models.py:95`, `:101`; `coordinator/loop.py:245`.

**What breaks / scenario:** ChatPayload rejects replies above 8 KiB before the worker handler's 64 KiB limit can run; Runtime quarantines that frame as processed instead of invoking the worker error handler. The Manifest model accepts up to 200 capabilities, but the State candidate accepts only 100; check reasons also cap at 100 even though many people/capability checks can exceed that. A worker reply can pass external validation and fail later when projecting the decision. With the real renderer wired, that projection happens in the preview callback: `_retry` is bypassed and the dispatcher marks the effect failed, potentially stranding the completed job without a question. Deadline retries for rejected chat frames do not repair failed callbacks for jobs already marked done.

**Exact fix:** define shared bounded limits that fit the chat transport, checker, State and render props. Validate projection compatibility inside the guarded worker-validation branch before committing job completion or scheduling renders. Treat any rejected worker payload as the same one-retry-then-visible-failure case. Reject oversized frames through an attributable worker error where safely identifiable.

### F18 — minor — Repeated replacements and persisted caches have no lifecycle bound

**Location:** `coordinator/loop.py:313`, `:383`; `coordinator/switch_client.py:253`, `:270`; `coordinator/ledger.py:24`.

**What breaks / scenario:** each unauthorized answer immediately issues a new question with a fresh two-hour expiry, without a replacement cap/backoff. `questions.json` retains every exact payload and is read/rewritten whole; workflow releases are never pruned even though visible releases cap at 200. Eventually the workflow exceeds the 1 MiB ledger limit or cache rewrites dominate. These are not bounded merely because one outbox page has a limit.

**Exact fix:** cap automatic replacement attempts within the original decision deadline, then visibly hand off; rate-limit reissues. Store immutable question payloads once in SQLite and archive bounded active references. Store releases as independent rows rather than an ever-growing workflow JSON blob. Preserve dedupe/decision history when compacting.

### F19 — minor — Render diagnostics are discarded

**Location:** `coordinator/render_bridge.py:49`, `:61`; `coordinator/dispatcher.py:208`.

**What breaks / scenario:** a renderer schema/dependency/font failure becomes only "preview unavailable" because stderr is discarded and exceptions are reduced to type/generic text. The user has no actionable reason during the four-day build. The live API's two `message failed` entries similarly cannot reveal their HTTP status or failed destination; W3 cannot establish their cause from allowed GET evidence.

**Exact fix:** retain a bounded, sanitized renderer diagnostic and structured HTTP status/destination/effect reference in the ledger; expose a concise reason without payloads, tokens or arbitrary raw logs. Keep a strict stderr cap and timeout. Do not attribute the observed live failures to missing membership without evidence.

### F20 — minor — Crew text and duplicate state machinery add avoidable integration work

**Location:** `coordinator/dispatcher.py:175`; `coordinator/config.py:19`, `:25`; `coordinator/loop.py:43`; `coordinator/runtime.py:185`; `coordinator/dispatcher.py:215`.

**What breaks / scenario:** crew text displays raw IDs and full ISO timestamps, omits named call times and coverage, and says `Release r2` instead of the intended readable release summary. Runtime uses `document:<name>` while Dispatcher uses `doc:<name>`, so ownership/reconciliation state is duplicated. `take_two_supervisor_agent_id`, `take_two_ad_agent_id`, `take_two_tz` and workflow `source_responses` are unused. Exact question payloads live both in SQLite and a separate JSON cache; workflow/visible/table copies require manual synchronization and already drift (F13). There is also no implemented logistics-only render bypass: all passing candidates go through preview (`loop.py:252`).

**Exact fix:** keep the current architecture, but use one canonical document key and one question-payload store, remove unused settings/state, centralize projections, and format crew-facing names/times from the release envelope. Implement the promised explicit logistics path if it remains in demo scope. Avoid a coordinator rewrite or another service during the hackathon.

## Switch protocol audit and runtime facts learned

Every call in `coordinator/switch_client.py` was matched to the pinned source, not a live Switch request:

| Client call | Source and conclusion |
|---|---|
| Register `POST /agents` | `api/handlers.py:206`, `api/schemas.py`; custom connector, personal bearer registration and integration profile shape agree. |
| List/invoke ops | `api/operations.py:287`, `:296`, `:356`; connection header and `{result: ...}` envelope agree. |
| Connect production | `operations/definitions.py:252`; `room_id` and returned room/document metadata agree. |
| List/load/create/update documents | `definitions.py:471`, `:528`, `:555`, `:595`; parameters and result IDs agree. Document metadata really includes name and creating agent (`bridges/resource/service.py:169`). |
| Roles/targeted messages | `definitions.py:1035`, `:804`; holder objects and registered-name status keys agree. The server prepends mentions; F1 is the application mismatch. |
| Explicit text/media | `api/handlers.py:467`, `:525`; `{room_id, content}` and multipart file/caption/thread agree. A text receipt is not bridge delivery confirmation (F10). |
| YAML room provisioning | `definitions.py:1597`; room result model agrees for single-room templates. Runtime does not use this for shoot days (F4). |
| Questions/open/close/delivered/outcomes | `api/activity_routes.py:231`, `:264`, `:274`, `:286`; paths, snake_case opening payload and camelCase HTTP response model agree. Stream outcomes are snake_case; stored answers contain `question_id`, `selected_option_ids`, `custom_text` (`session_activity/service.py:799`). |
| WebSocket and heartbeat | `api/handlers.py:1198`, `:1350`; protocol 9 query parameters, positions and application pong agree. `scope=all` covers member-room conversation independently of the production room claim (`protocol/stream.py:693`). |

**Source wins:** the server preserves addressed message bodies; a JSON field named `addressed_to` does not strip the human-readable mention. A timely server answer stays answered after expiry (`session_activity/service.py:489`); closing a settled request leaves it settled (`:529`). Opening connection state precedes catch-up and owed outcomes can precede room replay. The source provides no atomic SQLite-to-Discord transaction. The license is Apache 2.0 limited by modified Commons Clause (`E:/DevDrive/switch/LICENSE:4`), not an unqualified Apache license.

W3 made no new real-Switch port/error observations. W1's reported 8000/3000/8065 services and Docker provenance remain W1 evidence. W3 independently observed only the local 8787 GET result described above.

## Review of Claude's review

Read `work/CLAUDE-REVIEW-W1.md` after the independent source trace.

| Claude item | W3 assessment |
|---|---|
| C1 render inputs | Agree on blocker and separate manifest/props hashes. Correct "every render fails": raw preview props can inherit defaults and render misleading media. Schema registration alone does not parse CLI props. See F2. |
| C2 discarded errors | Agree; cap and sanitize diagnostics rather than exposing arbitrary stderr. F19. |
| C3 crew text | Agree on names/readable times and operational details. Cosmetic paper colours are secondary to correct complete snapshots, holds and call times. F13/F14/F20. |
| C4 day formatting | Minor presentation issue. Contract permits a string; a bare ISO day is not itself a safety defect. Put day number/display date into trusted render props, not a fabricated approval. |
| C5 reset | Useful rehearsal tooling after correctness fixes. Preserve identity and archive the ledger; explicitly reconcile/close prior pending effects/questions before a reset with the same Switch identity. Reset must not import fictional approvals. |
| C6 live failures | Cause remains unproven under GET-only scope. Generic notices are insufficient diagnostics; F19. |
| C7 worker parsing | Agree; source and current agent instructions prove it. Prefer a narrow documented envelope over a general "find any braces" heuristic. F1. |

Claude's review does not cover F3, F5, F6, F8–F18. Passing tests and honest initial state do not resolve those findings.

## Needs the human

No user action or credential was needed to complete this review. Implementation owners must fix the blockers before a meaningful external rehearsal. After those fixes:

1. Confirm the deployed Switch build corresponds to the required checkout using the Docker-capable terminal; W3 did not inspect the running image.
2. Configure authenticated director/producer/AD/safety identities and actual crew transport identities privately in local configuration. Never substitute display names.
3. Attach the two distinct Console workers to production, assume their exclusive roles, allow coordinator addressing, and configure their sender IDs/registered names.
4. Connect Discord in Switch, link the owner's account, and provision the crew/day rooms using the repaired durable setup path.
5. Approve the checked initial schedule through Switch; verify r1 media from a crew account. Rehearse F1–F18 failure scenarios, then the exact two-change story and current-release confirmation. No new token/account should be created merely to work around these code defects.

## Self-review

Only this report was authored; test artifacts were confined to the permitted pytest/cache paths. Re-read the findings against the code and distinguished source evidence from live observations. Did not claim a new exploit test, render, Discord send or Switch error was executed.

| Must never happen | Review outcome |
|---|---|
| 1. Unapproved/stale plan reaches crew | Named approval checks exist; F2/F3/F6/F14 leave content/currentness gaps. |
| 2. Restart duplicates release, loses decision, reopens answered question | SQL outcome dedupe/exact payloads are present; F8 loses timely answers; F3/F9 lack complete recovery. Closing an answered Switch question does not reopen it. |
| 3. Non-authority decision releases anything | No direct browser reporter-spoof release bypass found. Runtime makes browser changes pending; outcomes check exact authorized identities. Preserve these checks in fixes. |
| 4. Silence picks an option | No default-selection path found. F8 concerns discarded real answers and missing expiry notices, not selection on silence. |
| 5. Every failure has timeline and visible message | Violated by F12; F19 limits diagnosis. Startup/stream failures can only be seen locally when transport is unavailable. |
| 6. Bounded loops/retries/queues/payloads | Many useful caps exist; F9/F17/F18 expose missing recovery/compatible bounds/lifecycle caps. |
| 7. Bad JSON gets one retry without crashing coordinator | Naked malformed JSON has tests; real instructed envelopes fail (F1), and pre/post-validation mismatches bypass the worker error path (F17). |

Five adversarial attempts, performed as source traces plus the existing test suite:

1. Sent the instructed mention/fenced shape through the parser mentally, then followed the retry/job handoff: F1.
2. Matched production-generated preview/call-sheet dictionaries field by field to schema and Remotion default merging: F2/F14.
3. Placed a location refusal and a timely answer during downtime, and moved restart past expiry: F3/F8.
4. Changed a pending candidate's location permission, then an unrelated scene, then Maya's hard stop while s3 was unresolved: F5/F16.
5. Timed out media before final text, then replied to the old PNG and confirmed after partial publication: F9–F11/F13.

## The first place the FLOW story breaks

1. **Normal day:** startup loads script/constraints documents, but holds every scene and has no initial planning command. Even using W1's per-scene preferences workaround, FLOW's initial three-scene schedule cannot be represented as one candidate/one card/one r1 (F4). Creating the day room and its documents is also absent. The earliest representational break is normal-day schedule proposal/approval, before Change 1.
2. **If a legitimate r1 is supplied through a future fixed initialization path:** Producer's rooftop refusal records r2, holds s3 and queues Supervisor after the constraints document. Hold text is generic and lacks the explicit rooftop warning. The real Supervisor's instructed fenced/addressed reply fails at `loop.py:204`. **This is the first break in the requested rooftop-to-release sequence: Change 1, step 4.** No AD job follows (F1).
3. **If parser compatibility is fixed:** AD's three manifests are checked; courtyard beyond 17:00 fails, stairs and park can pass given full setup/wrap/light facts. Two preview requests run, but F2 gives incompatible props/default labels. Production never receives the sketches (F7). The card can open with text labels only.
4. **Maya's free-text report / AD confirmation:** pending report exists; authenticated `/change person maya hard_stop 18:00` makes r3, closes the old question, cancels jobs and discards pending candidates. It holds s2 as well as s3. A new Supervisor/AD round can reject park and offer stairs full/reduced, but s2 stays held even after the s3 choice (F5). Unknown day-two availability remains nonpassing, as intended.
5. **Director choice / release:** authenticated current candidate selection can atomically commit one logical release/outbox. Real call-sheet input is incompatible and falls back to incomplete text (F2/F14). Media/text must be separately reconciled; a timeout currently strands publication, while Switch text acceptance can falsely mark external publication complete (F9/F10).
6. **Dev stale reply / confirmation:** explicit r1 text or a reply mapped to the r1 text post can trigger correction; a reply rooted on its PNG/MP4 is missed (F11). Explicit recognized `confirm r2` is required and deduped, but affected-person calculation, carried duties and call times remain incomplete (F13).

**The first place the FLOW story breaks: initial full-schedule approval from a clean ledger; assuming that precondition is repaired, the instructed Script Supervisor reply at Change 1 step 4.**
