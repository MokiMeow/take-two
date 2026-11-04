Take Two preserves the common loop, holds, two speeds, release states, and the agreed A+B demonstration.  
All four critical Switch integrations are supported by the pinned source, but their implementation contracts are incomplete.  
The largest gaps are constraint completeness, authority enforcement, stale-work races, and external publication recovery.  
Reviewed commit `989225d8`; no files changed, installations, Docker execution, or external posts. Runtime reliability is **not verified**.  
Verdict: **ready with fixes**.

1. **Make the retained agreement and missing requirements explicit — `docs/ARCHITECTURE.md`, `docs/PLAN.md`.**

   The plan faithfully retains two reasoning agents, a deterministic coordinator, immediate holds, creative and logistical paths, named decision types, separate release states, unknown permissions, scenarios A+B, and the real shortened-availability shoot. [DEMO.md:14](</C:/Users/Mohith S/Desktop/take-two/docs/DEMO.md:14>) matches the agreed real-shoot requirement.

   The omissions are substantive: setup/wrap duration, verification of required capabilities, named location-permission authority, serialized release commitment, and recovery from uncertain publication. These were explicit requirements in [ROUND3-SOL.md:82](</C:/Users/Mohith S/Desktop/take-two/debate/ROUND3-SOL.md:82>) and [ROUND3-SOL.md:114](</C:/Users/Mohith S/Desktop/take-two/debate/ROUND3-SOL.md:114>).

   **Add this rule:**

   > Demo acceptance includes declared setup/wrap time, required capabilities, named permission authority, serialized revision checks, and failed-publication recovery. A full inventory system remains outside scope.

   Also restore a reviewed scene breakdown between script lock and scheduling; [FLOW.md:6](</C:/Users/Mohith S/Desktop/take-two/docs/FLOW.md:6>) currently jumps directly to the AD’s schedule.

2. **Specify how Console agents acquire roles and accept delegation — `docs/AGENTS.md`, `docs/SWITCH-NOTES.md`.**

   **Yes:** Console-managed Claude Code and Codex agents can hold exclusive roles and receive role-addressed messages from the coordinator. The operations acquire session-backed leases and route `target_roles` to their live holders. See [definitions.py:804](/E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:804) and [definitions.py:1131](/E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:1131).

   However, “one session per role” is insufficient: one agent identity cannot hold both roles, and an unoccupied role produces no target-status entry.

   **Add:**

   > Create two distinct Switch agent identities. Each connects to `#production` and explicitly assumes its exclusive role. Configure both agents to accept coordinator-originated messages. Before delegation, verify the expected holder and presence; inspect `target_statuses`. Missing, unavailable, or `not_permitted` targets become visible failures.

   Addressing permission is independent of role occupancy. [agent_core.py:1961](/E:/DevDrive/switch/core/switch_core/bridges/agent/protocol/agent_core.py:1961).

3. **Define the custom coordinator’s question identity — `docs/SWITCH-NOTES.md:19`.**

   **Yes:** a custom agent can open `kind: questions` without a CLI session. The route accepts a caller-supplied session identifier; `open_approval` checks room membership and request content, without requiring a registered CLI session. [activity_routes.py:231](/E:/DevDrive/switch/core/switch_core/bridges/agent/api/activity_routes.py:231), [service.py:358](/E:/DevDrive/switch/core/switch_core/session_activity/service.py:358).

   **Replace the abbreviated question contract with:**

   > Persist a coordinator-generated UUID as the logical `session_id`; reuse it after restart. Generate and persist `turn_id` and `request_id` for each decision cycle. POST `/agent-sessions/{session_id}/approvals` with `kind: "questions"`, `options: []`, populated `questions`, explicit production `room_id`, `thread_id: null`, and a timezone-aware expiry. Enable `allow_custom_answer`. Persist the exact opening payload before sending it.

   The logical session identifier is application-chosen, not a worker’s session ID or a reconnecting socket’s identity. Identical retries are idempotent; changed content under the same request identity conflicts. [service.py:437](/E:/DevDrive/switch/core/switch_core/session_activity/service.py:437).

4. **Correct the promise of director-only cards — `docs/AGENTS.md:31`, `docs/ARCHITECTURE.md:69`.**

   Switch authorizes answers through the coordinator’s addressing policy, rather than a per-question film-role ACL. The first accepted answer settles the request. Merely checking the actor afterward does not keep the card open for the director. [service.py:465](/E:/DevDrive/switch/core/switch_core/session_activity/service.py:465).

   **Use this exact rule:**

   > Store authorized answerer identities with each decision. Validate `answered_by` against that set before accepting an outcome. An unauthorized settled answer releases nothing; record it and issue a replacement request. Do not claim per-card restriction unless the configured addressing policy actually provides it.

   Add location permission to the authority table. Replace “only the director can release” safety holds with:

   > Anyone may hold. Release requires recorded clearance from the named responsible person and successful hard-constraint checks. Creative approval cannot override refused permission or an unresolved safety restriction.

5. **Document the actual Discord attachment operation — `docs/SWITCH-NOTES.md:21`, `docs/ARCHITECTURE.md`.**

   **Yes:** MP4 and PNG bytes have a supported outbound path. For Python, it is multipart **`POST /agents/{agent_id}/rooms/{room_id}/media`**, using `file` or repeated `files`, plus optional `caption` and `thread_id`. Console’s `send_attachment` tool wraps this path; it is not a generic `/ops/send_attachment` operation. [handlers.py:525](/E:/DevDrive/switch/core/switch_core/bridges/agent/api/handlers.py:525).

   The bridge invokes the Discord adapter’s native file upload, including webhook posting under the agent identity. [collaboration_core.py:2740](/E:/DevDrive/switch/core/switch_core/bridges/collaboration/collaboration_core.py:2740), [adapter.py:1002](/E:/DevDrive/switch/core/switch_core/bridges/collaboration/discord/adapter.py:1002).

   **Add:**

   > Upload real bytes with appropriate MIME types. Test both MP4 playback and PNG opening from a crew account. Switch upload success is not Discord delivery confirmation. Relay limits or upload failure can produce a text failure notice.

   A GIF still depends on the same attachment transport; it is not a transport fallback.

6. **Make YAML provisioning and document ownership compatible — `docs/ARCHITECTURE.md:42`, `docs/SWITCH-NOTES.md:17`.**

   **Yes:** the coordinator can create a Discord-bridged room from YAML. Ordinary room provisioning does not require the managed-agent feature. It does require an owner and an existing configured bridge. [definitions.py:1597](/E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:1597).

   **Add:**

   > Use `room.bridge` equal to the configured Discord bridge’s display name; set `channel_type` explicitly, list the coordinator under `agents`, and resolve crew usernames on that bridge. If using `{$creator}`, link the owner’s Discord identity first. Persist the returned room ID and inspect `failed_attachments`.

   Bridge-name resolution and linked-identity requirements are implemented at [rooms_yaml.py:1244](/E:/DevDrive/switch/core/switch_core/rooms_yaml.py:1244) and [rooms_yaml.py:955](/E:/DevDrive/switch/core/switch_core/rooms_yaml.py:955).

   **Also add:**

   > Templates create room structure. Create mutable canonical documents afterward through the coordinator’s `create_room_document` operation.

   YAML inline documents are created for the human owner, whereas agent updates require the creating agent. [rooms_yaml.py:1376](/E:/DevDrive/switch/core/switch_core/rooms_yaml.py:1376), [definitions.py:602](/E:/DevDrive/switch/core/switch_core/bridges/agent/operations/definitions.py:602).

7. **Complete the connection and multiroom contract — `docs/SWITCH-NOTES.md:7`.**

   The stated **10-second interval and 30-second TTL are correct** at this commit. The WebSocket heartbeat mechanism needs clarification: the server sends an application `ping`, and the client replies with `{"type":"pong","cursor":...}`. [liveness.py:25](/E:/DevDrive/switch/core/switch_core/bridges/agent/protocol/liveness.py:25), [handlers.py:1218](/E:/DevDrive/switch/core/switch_core/bridges/agent/api/handlers.py:1218).

   **Add:**

   > Persist a connection UUID and event position. Open with `scope=all`, `filter=all` so ordinary crew reports are observable. Keep room-bound document/delegation operations connected to production; use explicit-room message/media routes for crew publication. Process application pings promptly, handle control frames, and stop on `taken_over`.

   Room-bound operations infer their room from connection context and can fail when none or several are bound. [context.py:92](/E:/DevDrive/switch/core/switch_core/bridges/agent/operations/context.py:92). The existing operation-envelope claim is correct. [operations.py:356](/E:/DevDrive/switch/core/switch_core/bridges/agent/api/operations.py:356).

8. **Specify deterministic report ingestion and worker dependencies — `docs/FLOW.md:15`, `docs/AGENTS.md`.**

   A coordinator “with no LLM” cannot silently acquire a general natural-language fact parser. Step 4 also delegates to the AD before the Supervisor has supplied the `must_keep` list that the AD supposedly receives.

   **Add:**

   > Accept a small documented structured change command containing entity, field, value, reporter and source message ID. Unknown free text becomes a pending report requiring normalization or confirmation. Deduplicate reports by message ID. Obtain the Supervisor’s requirement response before requesting final AD candidates.

   Worker replies must include `job_id`, both source revisions, and an explicit coordinator address. Discard stale replies. Give each job a deadline, one retry, and a visible failure state. On new inputs, invalidate pending jobs and renders as well as questions.

9. **Supply enough data for the checker’s promised verdict — `docs/ARCHITECTURE.md:93`.**

   The sample has availability and location permission, but no candidate schedule, capability availability, setup/wrap time, or complete travel contract. A `needs` list alone cannot verify privacy or equipment.

   **Replace the schema rule with:**

   > Each candidate resolves to a full manifest containing scene/shot IDs, assigned people, location, start/end, setup/wrap duration, required capabilities and source revisions. Constraints declare timezone, availability, hard stops, permission/window status, directed travel durations and verified capability status. Missing required facts are `unknown`.

   Use three checker outcomes: `pass`, `fail`, `needs_verification`. Only `pass` candidates become executable approvals. Verification creates a new constraints revision and triggers another check. Include `+05:30` or an explicit `Asia/Kolkata` policy; the existing timestamps are timezone-naive.

10. **Repair the demonstration’s feasibility contradiction — `docs/FLOW.md:19`, `docs/DEMO.md`.**

    The Supervisor says privacy is required, yet the park—with people walking past—passes. That makes the checker appear decorative.

    **Replace the story rule with:**

    > The confession must remain intelligible and confidential within the story. A visually secluded setting is a creative preference. Both candidates meet the hard requirement; the park sacrifices visual intimacy.

    Alternatively, keep privacy hard and replace the park with a verified private alternative.

    Also give both candidates explicit times, durations and light windows. Then the 18:00 hard stop can demonstrably invalidate the park’s 18:15 finish. “Move to day 2” requires confirmed day-two cast and location availability; otherwise present it as unresolved postponement.

11. **Close the approval-to-publication race — `docs/FLOW.md:35`, `docs/ARCHITECTURE.md:62`.**

    The current flow checks revisions, then renders, then publishes. Another change can arrive during rendering. Sharing a manifest also does not automatically guarantee identical artifact interpretation.

    **Add:**

    > Serialize change acceptance and release commitment per production. Bind decisions to request ID, source revisions, candidate ID and coordinator-computed manifest hash. Recheck after asynchronous work and immediately before dispatch. Commit the release and outbox entries atomically; obsolete queued effects must not dispatch.

    Hash canonical manifest content excluding its hash field. Keep artifact hashes separately. Reuse a preview only when its manifest hash matches the approved candidate. Stamp release identity without mutating approved creative content.

    If a newer change arrives during an external send, record the ordering and issue the hold; do not promise an atomic transaction spanning SQLite and Discord.

12. **Define recovery beyond “duplicates are ignored” — `docs/ARCHITECTURE.md:124`, `docs/FLOW.md:47`.**

    SQLite is authoritative for local decisions and effects, not merely “recovery only.”

    **Replace that description with:**

    > Persist the inbox, processed event position, immutable question payloads, render jobs, releases, acknowledgments and publication outbox. Deduplicate outcomes by `(session_id, request_id)`. Commit processing before calling `delivered`. On restart, restore identity, reconcile documents, fetch undelivered outcomes, and resume unfinished effects.

    Switch supports durable positions and retention-gap reporting. Outcomes remain owed until acknowledged, but this does not mean periodic retransmission on an otherwise healthy stream. [event_buffer.py:23](/E:/DevDrive/switch/core/switch_core/bridges/agent/protocol/event_buffer.py:23), [outcomes.py:1](/E:/DevDrive/switch/core/switch_core/session_activity/outcomes.py:1).

    **Publication rule:**

    > A timeout after sending is `uncertain`. Reconcile before retrying where possible. Retries retain the same logical release ID; duplicate visible posts are possible.

13. **Separate invalidation, delivery and acknowledgment — `docs/ARCHITECTURE.md:79`, `docs/FLOW.md:36`.**

    A release can become invalid before its successor exists. The current diagram only supersedes it when a replacement publishes.

    **Add:**

    > Track validity and holds independently of release progress. A newly invalid scene becomes unusable immediately; unaffected instructions remain valid. Track publication per destination and artifact, including pending, uncertain and failed status.

    Define expected recipients and acknowledgment deadlines. Count only a recognized crew identity explicitly confirming the current release ID. Unqualified “yes” remains ambiguous.

    For partial updates, either require everyone to confirm the new complete snapshot or carry forward unchanged duties explicitly and request fresh confirmation only from affected people. The “3 of 3” display must identify which policy it uses.

14. **Keep the stack, but make setup and rendering concrete — `docs/ARCHITECTURE.md`, `.env.example`, `README.md`.**

    Python plus a small Node/Remotion renderer and Console workers is buildable in principle. Four-day delivery is **not verified**. A TypeScript coordinator removes one language boundary only if it is already the builder’s stronger stack; rewriting during the event is a poor trade.

    **Add:**

    > Run one coordinator process, one fixed renderer bundle, and two worker identities. Invoke the Node renderer through a bounded subprocess using absolute paths and manifest files. Pin exact package versions; prepare the browser during setup. Pass identical props to composition selection and rendering.

    These APIs support parameterized video and PNG output. [renderMedia](https://www.remotion.dev/docs/renderer/render-media), [renderStill](https://www.remotion.dev/docs/renderer/render-still).

    Add timezone and artifact-directory configuration. Document that `DISCORD_BOT_TOKEN` configures the Switch bridge. Pin deployed Switch images/runtime artifacts as well as the source checkout.

15. **Move trustworthiness ahead of the real shoot — `docs/PLAN.md`, `docs/RISKS.md`.**

    Day one’s abandonment test already requires invalidating an old choice, but revision binding is scheduled for day three. Day three combines recovery engineering with friends arriving for filming.

    **Replace the sequence with:**

    > Day 1: prove registration, one worker, custom question, template-created Discord room, real MP4/PNG delivery, and minimal revision rejection within six focused hours. Day 2: add the second worker, two checked compromises, holds, duplicate-outcome handling, restart recovery and failed-publication tests. Day 3: rehearse before noon, freeze the shoot path, then film. Day 4: reproduce, record and submit.

    Cut client rooms, sun calculations, live takeover, general rewriting and arbitrary rescheduling first. Preserve A+B, two previews, holds, current-release confirmation and template provisioning.

    Text fallback may keep operations moving after render failure; it does not satisfy the promised visual demo.

16. **Correct evidence labels and submission details — `docs/SWITCH-NOTES.md`, `docs/RISKS.md`, `docs/PLAN.md`.**

    Replace “corrected by Sol’s review” with:

    > Reviewed against `989225d8`; source-supported capabilities are distinguished from issue reports and runtime checks still to perform.

    The exclusions are sound: tasks remain documented as unready; agent events exclude reactions; budgets cover agents/workspaces and can overshoot; stopping a template run prevents further room creation. [agent-protocol.md:222](/E:/DevDrive/switch/docs/official/internals/agent-protocol.md:222), [types.py:197](/E:/DevDrive/switch/core/switch_core/bridges/agent/protocol/types.py:197), [budgets.py:1](/E:/DevDrive/switch/core/switch_core/budgets.py:1), [agent_runs.py:455](/E:/DevDrive/switch/core/switch_core/agent_runs.py:455).

    The six issue descriptions match published reports: [#1335](https://github.com/sandbox-quantum/switch/issues/1335), [#1158](https://github.com/sandbox-quantum/switch/issues/1158), [#1005](https://github.com/sandbox-quantum/switch/issues/1005), [#1202](https://github.com/sandbox-quantum/switch/issues/1202), [#1226](https://github.com/sandbox-quantum/switch/issues/1226), [#1095](https://github.com/sandbox-quantum/switch/issues/1095). [PR #1317](https://github.com/sandbox-quantum/switch/pull/1317) remains unmerged. Root questions avoid one risky path; they do not fix kickoff activity cards generally. Console’s native-server fallback also encounters the reported Windows setup problem.

    Keep workflow construction inside the event window. If entering Wispr, capture genuine proof during building and include it before the relevant submission closes. Existing libraries/templates are allowed; the Switch workflow must be built during the hackathon. [Official FAQ](https://www.wemakedevs.org/hackathons/switch).