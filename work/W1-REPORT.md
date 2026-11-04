# W1 report

Implemented the coordinator and verified its real Switch registration, documents and native Mattermost question. The local Control Room runs at http://127.0.0.1:8787. The normal coordinator was reconnected after the probe and is left running as PID 28140; a real production-scoped `list_roles` call succeeded. Docker CLI inspection and provenance of the already-running server image remain unverified from this sandbox.

## 1. Done

1. **Server: partially verified.** `/health` and `/health/ready` return HTTP 200; `/health` returns `{"status":"ok"}`. Mattermost's ping returns 200. `docker ps` is denied access to the engine pipe and Docker config. Source-build setup checks checkout `989225d8a13f6f36359c54f52d86aec01c4e0826`, uses the standalone Compose file, builds Switch/Gateway/setup from that checkout, and keeps configuration in this project: `scripts/switch/prepare.py:15`, `scripts/switch/compose.override.yml:5`, `scripts/switch/start.ps1:1`. Source files were not edited; no git commands ran.
2. **Tests: done.** `UV_CACHE_DIR` set to `data/uv-cache`, then `uv run pytest -q --basetemp=data/pytest-final-after-live`: **190 passed, 1 skipped, 1 warning**. Checker alone: **62 cases**. The skip requires Windows symlink privileges; the warning is Starlette using a deprecated AnyIO alias. Python is 3.12.10, bounded by `pyproject.toml:6`; dependencies are locked. See `coordinator/checker.py:32`, `coordinator/tests/test_checker.py:62`.
3. **Real Switch probe: done.** Personal-key registration succeeded and persisted `data/identity.json`. One WebSocket connection stayed open **300.09 seconds with one connection opening and no reconnect**, from 08:55:57 to 09:00:57 IST on 4 November. A private `production` Mattermost room was created from the production template with the coordinator attached; exclusive worker roles exist without fabricated worker identities. Real `script-r1` and `constraints-r1` documents were created. A native question opened with state `open`; an identical retry returned 200 and left one matching post. The seeded human account can read that post, with one attachment and one action. Evidence: `data/live-w1-proof.json`, `data/mattermost-proof.json`. Probe: `uv run python -m scripts.live_w1_probe`, `scripts/live_w1_probe.py:23`.
4. **Live API: done.** `uv run python -m scripts.smoke_api` returned `state_http=200`, `state_valid=true`, `change_http=200`, `change_status=pending_confirmation`, `sse_update=true`, `constraints_unchanged=true`. `/` returned 200 for Claude's built UI; encoded media traversal returned 404. Implementation: `coordinator/api.py:167`, `coordinator/runtime.py:289`, `coordinator/__main__.py:10`. Browser reports require authenticated Switch confirmation; a supplied reporter string cannot grant authority.
5. **Fixtures: done.** Six snapshots, `fixtures/ui-state/01-normal.json:1` through `06-stale-reply.json:1`, validate against `coordinator/ui_models.py:180`. Film script, r1 constraints and crew YAML are in `fixtures/film/`. Tests: `coordinator/tests/test_ui_models.py:17`. Runtime starts with held scenes and no claimed approvals; it never imports fixture releases as real decisions (`coordinator/runtime.py:90`).
6. **Coordinator slice: done with external setup remaining below.** Durable inbox positions, atomic state/outbox, exact question payloads, SQL outcome dedupe, revision invalidation, Supervisor-before-AD, three-way checks, named authority, two-round Neither handling, explicit acknowledgments and stale-release corrections are implemented. `coordinator/ledger.py:62`, `coordinator/loop.py:124`, `coordinator/loop.py:289`, `coordinator/dispatcher.py:299`, `coordinator/runtime.py:216`. Tests cover restart checkpoints, uncertain sends, stale renders and publication callbacks. The render bridge invokes the specified bounded Node command; absent renderer produces a clearly named `.placeholder.txt`, never counterfeit MP4/PNG (`coordinator/render_bridge.py:23`). Templates: `templates/production.yaml:1`, `templates/crew.yaml:1`, `templates/shoot-day.yaml:1`.

## 2. Runtime facts learned

- Switch API: http://127.0.0.1:8000; Gateway UI: http://localhost:3000; Mattermost: http://localhost:8065. Readiness is `/health/ready`, separate from `/health`.
- First login is seeded, not a new signup: Mattermost username `user`, password named `MATTERMOST_USER_PASSWORD` in `scripts/switch/.env`; team `switch`, channel `production`. Gateway username `admin@switch.local`, password named `GATEWAY_ADMIN_PASSWORD` in that file. Both logins succeeded through their APIs. Read passwords locally in an editor; do not paste them into a report.
- **Personal key already created and configured.** For a fresh setup: log into Gateway as the intended owner, open **API Keys**, choose **Create API Key**, enter a label, create, copy the Registration Key privately into root `.env` as `SWITCH_REGISTRATION_KEY`. The API equivalent is authenticated `POST /gateway/api-keys` with `{"label":"Take Two coordinator W1"}`. Do not use the deployment bootstrap token as the coordinator's personal key.
- Initial Docker access failed; Console v0.40.1 was downloaded to `out/` and launched. Its UI could not be controlled because the native helper was unavailable. Only that exact process was stopped. No global software was installed. Issue #1335 was not reproduced or disproved. Later, the Switch HTTP services became available independently; real probes then succeeded.
- **Source wins:** pinned protocol implementation supports WebSockets, application ping/pong at 10 seconds and 30-second TTL, and protocol 9 positions. The internal protocol prose's SSE-only/2-second/6-second description is stale. See Switch `protocol/liveness.py:25`, `api/handlers.py:1218`, `protocol/stream.py`.
- **Source wins:** live HTTP question responses use camelCase keys, while opening requests use snake_case. Stored answer notes use `custom_text`. Agent message `sender_kind` can be null. Role holders use registered agent names; message senders use separate transport IDs. Mattermost `answered_by` uses its transport identity; Console can use `user:<UUID>`. The implementation accounts for these differences.
- **Source wins:** Switch LICENSE is Apache 2.0 limited by a modified Commons Clause. Attribution and the full license are included beside the adapted setup recipe; the Python protocol client is an original implementation guided by Switch's own runtime and handlers.
- **Source wins:** root `DISCORD_BOT_TOKEN` is not wired into Switch by this coordinator. Use Switch's per-bridge **Messaging apps → Connect → Discord** form. The separate distributed-app deployment path requires all four `DISCORD_APP_*` credentials plus a public messaging URL; do not partially configure it (`E:/DevDrive/switch/core/switch_core/config.py:1540`).

Redacted real request/response shapes; placeholders below contain no credentials:

```json
POST /agents
{"name":"take-two-coordinator","description":"Take Two deterministic production coordinator","connector_type":"take-two-coordinator","integration_profile":{"connection_model":"always_on","message_exchange":true,"pre_invocation_mediation":[],"post_invocation_mediation":[],"event_reporting":[]},"overwrite":false}
response: {"id":"<agent-id>","api_key":"<redacted>"}

POST /agents/<agent-id>/ops/create_room_document
X-Switch-Connection-Id: <persisted-connection-UUID>
{"name":"script-r1","description":"Take Two canonical input","instructions":"Agents propose; the coordinator checks; humans decide.","content":"<script JSON>"}
response: {"result":{"document_id":"<document-id>"}}

POST /agent-sessions/<persisted-session-UUID>/approvals
{"request_id":"<UUID>","turn_id":"<UUID>","kind":"questions","title":"Take Two W1 live connection check","detail":null,"options":[],"questions":[{"id":"choice","title":"Take Two W1 live connection check","prompt":"Can you see this native question? This transport check approves no shoot plan.","options":[{"id":"visible","label":"I can see the card","description":null}],"multi_select":false,"allow_custom_answer":true}],"room_id":"<production-room-id>","thread_id":null,"expires_at":"<aware ISO timestamp>"}
response: {"sessionId":"<UUID>","requestId":"<UUID>","kind":"questions","state":"open","answer":null,"answers":null,"answeredBy":null,"answeredAt":null,"expiresAt":"<UTC ISO timestamp>","deliveredAt":null}
```

The question is a transport check; answering it authorizes no shoot release. The probe intentionally does not acknowledge or advance business events it has not processed.

## 3. Needs the human

1. **Verify the running container provenance outside this sandbox.** Run `docker ps` in your normal terminal. The sandbox still cannot inspect Docker. The project now prepares source builds tagged `take-two-989225d8`; verify/rebuild with `scripts/switch/start.ps1` before relying on that pin. The pre-existing running image's correspondence to commit `989225d8` was not proven here.
2. **Open Mattermost** at http://localhost:8065, sign in as `user` with the private seeded password, open team `switch` → private `production`, and inspect the W1 question. The personal key and coordinator room ID are already in root `.env`; no need to recreate them.
3. **Name the human authorities.** Set `TAKE_TWO_DIRECTOR_ID`, `TAKE_TWO_PRODUCER_ID`, `TAKE_TWO_AD_ID`, and, when used, `TAKE_TWO_SAFETY_ID` / `TAKE_TWO_CAPABILITY_AUTHORITY_ID` in root `.env` to authenticated Switch transport identities. Have each human send a harmless message; its pending report shows the reporter ID. Update `fixtures/film/crew.yaml`'s `switch_identity` values to real crew IDs. Display names are insufficient.
4. **Create the two Console workers.** Use distinct registered identities, attach both to `production`, accept messages from the coordinator, and take the exclusive roles `script-supervisor` and `first-ad`. Claude/user supply their role instructions in `agents/`. Configure `TAKE_TWO_SUPERVISOR_AGENT_NAME`, `TAKE_TWO_AD_AGENT_NAME`, `TAKE_TWO_SUPERVISOR_SENDER_ID`, `TAKE_TWO_AD_SENDER_ID`. Names come from Console registration; sender IDs come from each worker's received message. Reply schemas are in `coordinator/workflow_models.py:18`; include job ID, both revisions, and coordinator address.
5. **Connect Discord.** In Discord Developer Portal create the bot, enable Message Content and Server Members intents, invite with bot/application-command scopes and channel/message/webhook/role/history/attachment permissions, and copy Guild ID. In Switch Console Home → Messaging apps → Connect → Discord, supply the bot token and Guild ID, then link the owner's Discord account. Use the connection's display name and real crew usernames in the crew/shoot-day templates. Set resulting room IDs in `SWITCH_CREW_ROOM_IDS`, comma-separated. Keep the token private; never send it in chat.
6. **Finish media and initial planning.** Claude supplies `render/cli.mjs`; verify real preview MP4 and call-sheet PNG in Discord from a crew account. Fresh state is held: start authenticated per-scene planning with `/change scene <scene-id> preferences <JSON-array>` and approve passing plans through Mattermost. Then rehearse the FLOW rooftop refusal and Maya hard-stop commands. Restart the coordinator after changing configuration: `UV_CACHE_DIR` = `data/uv-cache`, then `uv run python -m coordinator`.

## 4. Found, not fixed

- **Docker engine permissions / running-image provenance:** `scripts/switch/start.ps1:7`. Health is verified; `docker ps` and actual image-to-commit mapping need the normal terminal. Suggested fix: run the supplied checked-out-source build through the Docker-capable session. `scripts/switch/core-digest.txt` records a core image digest, but does not itself prove source equivalence or the Gateway/setup digests.
- **Renderer absent during verification:** `coordinator/render_bridge.py:45`. Explicit placeholder/text fallback works; real visual acceptance still requires Claude's renderer and Discord upload/playback verification.
- **No real reasoning-worker or Discord round trip yet:** `coordinator/runtime.py:115`, `coordinator/config.py:12`. Authenticated delegation/release/ack logic is unit-tested, but the named workers, human IDs and Discord bridge require the setup above. Fresh runtime deliberately has no pre-approved demo plan.
- **Docs to update, not edited:** `docs/UI-CONTRACT.md:5` should clarify that unauthenticated browser changes are reports requiring Switch confirmation. `.env.example:8` / Switch notes should distinguish per-bridge Discord credentials from the unused coordinator `DISCORD_BOT_TOKEN` name. `README.md:19` still describes planning-only status. The source-backed protocol/identity/license corrections above belong in the docs.
- **One platform-specific test skip:** `coordinator/tests/test_api.py:102`. Symlink containment is implemented; the live Windows account cannot create the test symlink. Re-run that case in an environment with symlink privileges.

## 5. Self-review

Re-read the implementation as a hostile reviewer and corrected issues found in review: nullable worker kinds, separate identity namespaces, native notes, wrong-scene candidates, unsafe carried-forward instructions, browser authority spoofing, event dedupe before effects, document ordering, queue bounds, pause races, and restart callbacks.

Seven invariants checked: crew receives only approved/current releases; commits and dedupe survive restart; only the named authenticated authority can approve; expiry picks nothing; failures appear in timeline and visible notices; queues/payloads/retries are bounded; malformed worker JSON gets one retry then a visible failure.

Five attempts to break it:

1. Answered stale and unauthorized cards, chose an invented candidate, then replayed the same outcome after restart: no extra release.
2. Injected crashes before commit, during uncertain media sends, and after sent-text checkpoint but before UI callback: rollback/reconciliation retained one logical release without automatic uncertain resend.
3. Proposed refused permission, unknown day-two facts, wrong scenes, overlapping unchanged duties, reversed travel and late wrap: checker rejected or required verification.
4. Sent bad/oversized JSON twice, delayed workers beyond deadlines, selected Neither twice, filled queues, and looked up dependencies after 1,000 completed effects: bounded failure or manual handoff.
5. Changed revisions during rendering/sending, paused readiness during reconciliation, replayed nullable-kind worker frames, spoofed a browser reporter, and requested encoded path traversal: stale work stopped, authenticated facts stayed unchanged, traversal returned 404.

No Switch source, docs, UI, renderer or agent-instruction files were edited. No git commands or global installations were used. Only processes started by this task were stopped. Generated test directories were moved under `data/`; deliverable source/fixture files use LF and remain below 500 lines.
