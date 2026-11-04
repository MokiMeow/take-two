# UI contract (coordinator ⇄ Control Room)

The **Control Room** is a web page (Vite + React + TypeScript, in `ui/`) that shows the production's live state. It is built by Claude. The coordinator (Python, in `coordinator/`) serves it and this API. Built by Codex.

**Switch stays the source of truth for humans.** The director decides through the native Switch question card in Mattermost, and crew confirm in Discord. The Control Room is a **read-mostly window** for the director and AD, and for the demo video. Its only write is reporting a structured change, which goes through exactly the same pipeline as `/change` in chat.

## Endpoints (coordinator, default `http://127.0.0.1:8787`)
| Method | Path | Returns |
|---|---|---|
| GET | `/api/state` | The full `State` snapshot below |
| GET | `/api/events` | Server-Sent Events. Each event is `event: state` with `data: <State JSON>`, sent after every committed change. A heartbeat comment every 15 s |
| POST | `/api/changes` | Body `ChangeCommand`. Returns `{ "change_id": "...", "status": "recorded" \| "pending_confirmation" \| "rejected", "reason"?: "..." }` |
| GET | `/media/<file>` | Rendered previews (`.mp4`) and call sheets (`.png`) from the artifacts directory; never anything outside it |
| GET | `/` and `/assets/*` | The built UI (`ui/dist`) |

CORS: allow `http://localhost:5173` in dev only.

## Types (JSON; times are ISO 8601 with `+05:30`)
```ts
type Validity = "valid" | "held" | "invalid";
type CheckResult = "pass" | "fail" | "needs_verification";
type DecisionStatus = "open" | "answered" | "expired" | "closed_outdated" | "rejected_unauthorized";
type ReleaseStatus = "approved" | "published" | "superseded";
type PublicationStatus = "pending" | "sent" | "uncertain" | "failed";
type JobStatus = "queued" | "running" | "done" | "failed" | "cancelled";

interface State {
  production: { id: string; title: string; timezone: string; now: string; day: string };
  revisions: { script: number; constraints: number };
  scenes: Scene[];
  changes: Change[];          // newest first
  jobs: Job[];                // current change only
  decision: Decision | null;  // the open or most recent decision
  releases: Release[];        // newest first
  crew: CrewMember[];
  timeline: TimelineItem[];   // newest first, capped at 200
}

interface Scene {
  id: string; number: number; title: string;
  hard: string[]; preferences: string[];
  validity: Validity; hold_reason?: string;
  plan?: { location: string; start: string; end: string; setup_min: number; wrap_min: number; people: string[] };
}

interface Change {
  id: string; at: string; reporter: string;
  reporter_name?: string;                  // trusted crew/authority display name
  recorded_at?: string;                    // ingestion timestamp; see time semantics below
  entity: "location" | "person" | "scene" | "capability";
  target: string; field: string; value: string;
  status: "recorded" | "pending_confirmation" | "rejected";
  source: "mattermost" | "discord" | "control_room";
  constraints_rev?: number;
}

interface Job { job_id: string; role: "script-supervisor" | "first-ad"; status: JobStatus; started_at: string; deadline: string; summary?: string }

interface Candidate {
  candidate_id: string; label: string;      // "Stairwell, reduced coverage"
  story_cost: string;                        // one sentence from the Supervisor
  check: { result: CheckResult; reasons: string[] };
  manifest: { scene_id: string; location: string; start: string; end: string; setup_min: number; wrap_min: number; people: string[]; shots: string[]; capabilities: string[] };
  manifest_hash: string;
  schedule?: Candidate["manifest"][];      // complete schedule for a multi-scene candidate
  preview_url?: string;                      // /media/....mp4, absent while rendering
  preview_status: "none" | "rendering" | "ready" | "failed";
}

interface Decision {
  request_id: string; status: DecisionStatus;
  question: string; authority: string;       // authenticated Switch identity (retained)
  authority_name?: string;                  // trusted display name, e.g. "Arun"
  bound: { script: number; constraints: number };
  opened_at: string; expires_at: string;
  candidates: Candidate[];                   // includes failed ones, so the UI can show why
  must_keep?: string[];                     // Supervisor's requirements for human review
  requirements_note?: string;               // describes which requirements the checker enforces
  answer?: { candidate_id: string | "neither"; note?: string; answered_by: string; answered_by_name?: string; at: string };
}

interface Release {
  release_id: string; number: number; status: ReleaseStatus;
  created_at: string; manifest_hash: string; summary: string;   // "Scene 3 moves to the stairwell, 16:30–17:15"
  call_sheet_url?: string; preview_url?: string;
  publications: { room: string; room_name?: string; platform: "discord" | "mattermost"; status: PublicationStatus }[];
  acks: { expected: string[]; confirmed: { person: string; at: string }[]; policy: "affected_only" | "everyone" };
}

interface CrewMember { id: string; name: string; role: string; role_label?: string; call_time?: string; acked_release?: number; affected?: boolean }

interface TimelineItem {
  at: string;
  kind: "change" | "hold" | "job" | "check" | "render" | "decision" | "release" | "ack" | "stale_reply" | "error";
  text: string;     // one plain sentence, already human readable
  ref?: string;     // id of the change / decision / release
}

interface ChangeCommand { entity: Change["entity"]; target: string; field: string; value: string; reporter: string }
```

## Rules
- The coordinator builds `State` from its SQLite ledger after each commit. The UI never computes validity, checks or authority.
- Field names are stable. Adding a field is fine; renaming or removing one needs a note in this file.
- W4 adds `Candidate.schedule`, `Decision.must_keep`, and `Decision.requirements_note`. `schedule` includes every proposed scene for an initial complete plan; `manifest` remains the representative scene. `must_keep` is human-reviewed prose, not a claim that every sentence is machine-checked.
- W5 adds `Decision.authority_name`, `Decision.answer.answered_by_name`, `Change.reporter_name`, `Change.recorded_at`, `CrewMember.role_label`, and `Release.publications[].room_name`. They are optional for older snapshots; newly created live objects populate them. Names come from reviewed crew/authority configuration; room labels come from configured destinations and the shoot-day template. IDs remain for joins and authorization. The UI displays the name fields, never parses Switch IDs. Unknown display identities use a descriptive label rather than an ID.
- For a recorded time change (`person.hard_stop`, `location.light_until`), `Change.at` is the full production-day timestamp used by the checker, normalized to the production timezone; `value` preserves exactly what was typed, such as `"18:00"`. For recorded `available`/`windows` lists, `at` is the earliest validated interval start. For other changes and unconfirmed reports, `at` remains the ingestion timestamp. `recorded_at` preserves ingestion time independently. This refines the previous ingestion-only meaning of `at` for time changes.
- `published` means **accepted by Switch for relay, not delivered**. Publication `sent` has the same acceptance meaning for that destination; neither proves Discord delivery, media playback, or a human reading it. Crew acknowledgments are separate.
- Only known crew/authority free text that no command, worker, acknowledgment, stale-reply, or native-question handler consumed can become a pending report. Coordinator/system/document chatter never becomes a change. Timeline text already uses trusted names. Invalid Unicode is rejected before persistence; state contains no lone surrogates.
- `fixtures/ui-state/*.json` holds example snapshots for each demo moment (normal, hold, two options, outdated, released, stale reply). The UI is developed against these.
