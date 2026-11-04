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
  preview_url?: string;                      // /media/....mp4, absent while rendering
  preview_status: "none" | "rendering" | "ready" | "failed";
}

interface Decision {
  request_id: string; status: DecisionStatus;
  question: string; authority: string;       // "Director (Arun)"
  bound: { script: number; constraints: number };
  opened_at: string; expires_at: string;
  candidates: Candidate[];                   // includes failed ones, so the UI can show why
  answer?: { candidate_id: string | "neither"; note?: string; answered_by: string; at: string };
}

interface Release {
  release_id: string; number: number; status: ReleaseStatus;
  created_at: string; manifest_hash: string; summary: string;   // "Scene 3 moves to the stairwell, 16:30–17:15"
  call_sheet_url?: string; preview_url?: string;
  publications: { room: string; platform: "discord" | "mattermost"; status: PublicationStatus }[];
  acks: { expected: string[]; confirmed: { person: string; at: string }[]; policy: "affected_only" | "everyone" };
}

interface CrewMember { id: string; name: string; role: string; call_time?: string; acked_release?: number; affected?: boolean }

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
- `fixtures/ui-state/*.json` holds example snapshots for each demo moment (normal, hold, two options, outdated, released, stale reply). The UI is developed against these.
