# Switch notes

Reviewed against Switch commit `989225d8` (2 Nov 2026). **Source-supported** means the Switch code allows it. The coordinator protocol, question cards, room documents, roles, media uploads and rooms from YAML below have all been exercised by `scripts/demo_day.py` against a real Switch server; Discord card buttons have not.

## Coordinator protocol
- **Register:** `POST /agents` with `connector_type` and an integration profile (`register-known` rejects custom types). It needs a registration credential; afterwards use the returned agent key as `Authorization: Bearer`. Use a **personal** registration key so the user owns the coordinator, not the bootstrap account. Store the identity and never re-register on startup (`overwrite: true` rotates credentials).
- **Live connection:** WebSocket `/agents/{id}/connection/ws`. Persist a connection UUID and event position. Open with `scope=all, filter=all` so crew reports are seen.
- **Heartbeat:** 10 s interval, 30 s expiry. On the WebSocket the server sends an application `ping`; reply with `{"type":"pong","cursor":...}`. The HTTP alternative is `/agents/{id}/connection/beat`.
- **`taken_over` is terminal.** Stop; don't blindly reconnect.
- **Events:** `message`, `command`, `room_join`, `approval_outcome`, `session_command`, plus control frames.
- **Operations:** `GET /agents/{id}/ops`, `POST /agents/{id}/ops/{op}` with `X-Switch-Connection-Id`; results come wrapped in `{"result": ...}`. Room-bound operations take their room from the connection context and can fail if no room or several rooms are bound. Keep document and delegation operations bound to `#production`, and use the explicit-room routes for crew posts.

## Question cards (the director's decision)
Source-supported: a custom agent can open `kind: questions` with no CLI session.
- Persist a coordinator-generated UUID as the logical `session_id` and reuse it after restarts.
- Generate and persist `turn_id` and `request_id` per decision cycle.
- `POST /agent-sessions/{session_id}/approvals` with `kind: "questions"`, `options: []`, filled `questions`, the explicit `#production` `room_id`, `thread_id: null`, a timezone-aware expiry, and `allow_custom_answer` (for "Neither + note").
- Persist the exact payload before sending. Identical retries are idempotent; changed content under the same `request_id` conflicts.
- Outcomes: `GET /agent-sessions/approvals/outcomes`. Then `POST …/{request_id}/delivered` once processed, or `…/close`.
- The first allowed answer settles the card. Allowed means the coordinator's addressing policy, not film roles, so check `answered_by` ourselves.

## Attachments to Discord
Source-supported: multipart **`POST /agents/{agent_id}/rooms/{room_id}/media`** (`file` or repeated `files`, optional `caption` and `thread_id`). Console's `send_attachment` tool wraps this; there is no `/ops/send_attachment`. The Discord adapter does a native upload under the agent's identity. Switch accepting an upload doesn't prove Discord delivered it, so test MP4 playback and PNG opening from a crew account.

## Rooms from YAML
Source-supported: `create_room_from_yaml` works for agents without `agent_management`. It needs an owner and an already configured bridge.
- `room.bridge` = the Discord bridge's display name; set `channel_type` explicitly; list the coordinator under `agents`.
- Crew usernames resolve on that bridge. Using `{$creator}` needs the owner's Discord identity linked first.
- Persist the returned room ID and inspect `failed_attachments`.
- Create mutable documents afterwards with `create_room_document`. YAML documents belong to the human owner, and only the creating agent can update a document.

## Roles
Source-supported: Console-managed Claude Code and Codex agents can hold exclusive roles and receive `target_roles` messages from the coordinator.
- One agent identity holds **one live role**, so we use two identities.
- An empty role produces no `target_statuses` entry.
- Permission to address an agent is separate from who holds the role.
- Roles route messages; they don't enforce turn order.

## Not used
- **Tasks protocol:** unfinished.
- **Budgets as a per-room cap:** budgets are per workspace or agent and can overshoot.
- **Emoji reactions as input:** not delivered to agents.
- **Template "stop" as cancel:** it stops further room creation, not running agents.

## Known issues (published reports, not reproduced here)
- **#1335:** Windows setup crashes with a system PostgreSQL 18. Console's native server hits it too.
- **#1158:** Mattermost activity card fails on template kickoff. PR #1317 was unmerged when checked. Root-level questions avoid one path, not all of them.
- **#1005:** the Mattermost bridge makes a new bot token on every start.
- **#1202:** deleting a room breaks agent replies, so archive rooms instead.
- **#1226:** Discord splits long code blocks, so keep messages short.
- **#1095:** room instruction edits don't reach live sessions.
