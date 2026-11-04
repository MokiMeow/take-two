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
  resolution?: "recorded" | "dismissed"; // W8: disposition of an original pending report
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
  duty_changes?: Record<string, string[]>; // W8: personal differences from last explicit confirmation
  publications: { room: string; room_name?: string; platform: "discord" | "mattermost"; status: PublicationStatus }[];
  acks: { expected: string[]; confirmed: { person: string; at: string }[]; policy: "affected_only" | "everyone" };
}

interface CrewMember { id: string; name: string; role: string; role_label?: string; call_time?: string; acked_release?: number; affected?: boolean; since_confirmed?: string[] }

interface TimelineItem {
  at: string;
  kind: "change" | "hold" | "job" | "check" | "render" | "decision" | "release" | "ack" | "stale_reply" | "error";
  text: string;     // one plain sentence, already human readable
  ref?: string;     // id of the change / decision / release
}

interface ChangeCommand { entity: Change["entity"]; target: string; field: string; value: string; reporter: string }
```

## Rules
- W6 report-form fields are `location: permission, window, light_until`; `person: hard_stop, available, late_by`; `scene: status, overrun`; `capability: status`. `windows` remains a JSON-interval-list alias. The current read-only UI source omits `location.light_until` and `scene.overrun` in `Shell.tsx`; its owner must add these entries. All commands work through authenticated Switch chat already. Browser reports still require authenticated confirmation in Switch.
- W6 authority mapping: `person.available`, `person.late_by`, and `person.hard_stop` use `availability_confirmation` (named human AD). Kit `status` uses `capability_verification` (AD plus configured camera/kit authority). Location `permission`, `window`, and `light_until` use the named producer/location authority. Scene `overrun` and `status` use `overrun_confirmation` (AD plus `TAKE_TWO_SCRIPT_SUPERVISOR_ID`, an authenticated human, separate from the worker identity). Unauthorised reports remain pending and never release anything.
- `late_by` is 0..1440 integer minutes from the earliest current released call (shoot start minus setup), intersected with known availability. `available 15:40` trims existing availability from that production-day time; it never extends the known end. Explicit JSON interval lists are still supported. `window 14:00-16:30` sets a producer-confirmed interval on the existing location's production day. `light_until` accepts HH:mm when the day is known, otherwise an explicit aware timestamp. These shorthand times populate the resolved `Change.at`, retaining the typed `value`.
- Capability `status unavailable` normalizes to trusted status `refused`. Reviewed constraints may declare `Scene.capability_alternatives`, e.g. `sound_recorder: [[lav]]`. A worker must include every capability of one reviewed replacement set, and each must be confirmed. Prose `must_keep` alone cannot authorize dropping sync sound: empty capability sets still fail the reviewed requirement. No replacement-availability window is added in W6.
- Scene `overrun 25` records the total extra photography minutes against the originally observed released start/end. It is monotonic and bounded to 1440; repeated reports never add the same delay again. The checker requires that original start and an end at least 25 minutes later. Setup, wrap, travel, hard stops, location windows and light still apply. `status held` holds a scene; only the same authority's `status scheduled` permits replanning it. Safety clearance remains separate.
- W6 replans exactly the held eligible scenes; deterministic delay projection includes downstream scenes forced by shared people/travel. Valid retained scenes are checker commitments. Every release is a full snapshot; chat lists each moved scene with old → new shooting times and each changed call with old → new call times. `acks.expected` is exactly the crew IDs whose duties differ from their own last explicitly confirmed release. Duties include call time and every assigned scene?s location, start/end, setup/wrap, role, and kit/coverage owned by camera/sound crew. Unchanged people carry forward. A relocation requires its assigned people; a recorder ? lav change requires the sound owner even with unchanged calls. This W8 rule replaces the W6 call-only policy.
- `fixtures/ui-state/day/NN-<beat>.json` are compact, real `/api/state` responses from `scripts/demo_day.py`, one after each recorded change, hold, opened decision, published release and completed confirmations. Record and hold share one atomic transaction, so their two snapshots can be identical. Existing `0N-*.json` fixtures are untouched.
- The coordinator builds `State` from its SQLite ledger after each commit. The UI never computes validity, checks or authority.
- Field names are stable. Adding a field is fine; renaming or removing one needs a note in this file.
- W4 adds `Candidate.schedule`, `Decision.must_keep`, and `Decision.requirements_note`. `schedule` includes every proposed scene for an initial complete plan; `manifest` remains the representative scene. `must_keep` is human-reviewed prose, not a claim that every sentence is machine-checked.
- W5 adds `Decision.authority_name`, `Decision.answer.answered_by_name`, `Change.reporter_name`, `Change.recorded_at`, `CrewMember.role_label`, and `Release.publications[].room_name`. They are optional for older snapshots; newly created live objects populate them. Names come from reviewed crew/authority configuration; room labels come from configured destinations and the shoot-day template. IDs remain for joins and authorization. The UI displays the name fields, never parses Switch IDs. Unknown display identities use a descriptive label rather than an ID.
- For a recorded time change (`person.hard_stop`, `location.light_until`), `Change.at` is the full production-day timestamp used by the checker, normalized to the production timezone; `value` preserves exactly what was typed, such as `"18:00"`. For recorded `available`/`windows` lists, `at` is the earliest validated interval start. For other changes and unconfirmed reports, `at` remains the ingestion timestamp. `recorded_at` preserves ingestion time independently. This refines the previous ingestion-only meaning of `at` for time changes.
- `published` means **accepted by Switch for relay, not delivered**. Publication `sent` has the same acceptance meaning for that destination; neither proves Discord delivery, media playback, or a human reading it. Crew acknowledgments are separate.
- Only known crew/authority free text that no command, worker, acknowledgment, stale-reply, or native-question handler consumed can become a pending report. Coordinator/system/document chatter never becomes a change. Timeline text already uses trusted names. Invalid Unicode is rejected before persistence; state contains no lone surrogates.
- `fixtures/ui-state/*.json` holds example snapshots for each demo moment (normal, hold, two options, outdated, released, stale reply). The UI is developed against these.
- W6 adds trusted `Location.exterior` constraints; exterior light is enforced even when a worker omits `Manifest.requires_light`. Native unauthorized answers permit at most one replacement card within the original expiry, then require human intervention. Confirmations for a release with unresolved scene holds are rejected. The kit shorthand `/change capability sound_recorder unavailable` maps to `capability.status` and uses the same authority check.

- W8 adds `Release.duty_changes` and `CrewMember.since_confirmed` (optional only for old fixtures). Both use deterministic personal duty comparison. `duty_changes` is frozen at release creation; `since_confirmed` recomputes after each explicit confirmation. `acked_release` retains the actual last explicit confirmation, including while a newer duty change is outstanding. Confirmed baselines persist beyond the 200-release UI history.
- After publication, each expected person gets a native single-choice Switch card: Confirm / Can't make it, with optional custom text. The request stores release ID, both revisions, exact payload, original expiry and named Switch identities. Wrong-person answers count for nothing and allow one replacement inside the same expiry. Supersession/revision changes close open cards. `confirm rN` remains available; expiry never confirms. ?Addressed? names are coordinator authorization, not per-card Switch ACLs. Discord buttons are source-supported but require a configured bridge; Mattermost uses its typed native-card answer grammar.
- Can't make it stores the authenticated person's note as a pending report without changing facts. Known crew constraint text asks the first-ad role for a bounded extraction reply, with message identity, production date and timezone. Strict schema/known targets/allowed fields and confidence >=0.9 are required. Ambiguous clock times remain pending; bare 6 resolves to 18:00 only when the known production availability admits one interpretation. The responsible human receives Record / Ignore. Record enters the same authority-checked `/change` transaction; Ignore sets `resolution: dismissed` on the original pending report. Successful Record sets `resolution: recorded`, while the original report retains its pending status and a separate authenticated recorded change provides the fact audit trail.
