// Mirrors docs/UI-CONTRACT.md. The coordinator owns every decision; the UI only displays.

export type Validity = "valid" | "held" | "invalid";
export type CheckResult = "pass" | "fail" | "needs_verification";
export type DecisionStatus = "open" | "answered" | "expired" | "closed_outdated" | "rejected_unauthorized";
export type ReleaseStatus = "approved" | "published" | "superseded";
export type PublicationStatus = "pending" | "sent" | "uncertain" | "failed";
export type JobStatus = "queued" | "running" | "done" | "failed" | "cancelled";

export interface ScenePlan {
  location: string;
  start: string;
  end: string;
  setup_min: number;
  wrap_min: number;
  people: string[];
}

export interface Scene {
  id: string;
  number: number;
  title: string;
  hard: string[];
  preferences: string[];
  validity: Validity;
  hold_reason?: string;
  plan?: ScenePlan;
}

export interface Change {
  id: string;
  at: string;
  reporter: string;
  entity: "location" | "person" | "scene" | "capability";
  target: string;
  field: string;
  value: string;
  status: "recorded" | "pending_confirmation" | "rejected";
  source: "mattermost" | "discord" | "control_room";
  constraints_rev?: number;
  reporter_name?: string;
  // Reports only: how a crew message was handled (W9).
  resolution?: "recorded" | "ignored" | "superseded" | null;
}

export interface Job {
  job_id: string;
  role: "script-supervisor" | "first-ad";
  status: JobStatus;
  started_at: string;
  deadline: string;
  summary?: string;
}

export interface Manifest {
  scene_id: string;
  location: string;
  start: string;
  end: string;
  setup_min: number;
  wrap_min: number;
  people: string[];
  shots: string[];
  capabilities: string[];
}

export interface Candidate {
  candidate_id: string;
  label: string;
  story_cost: string;
  check: { result: CheckResult; reasons: string[] };
  manifest: Manifest;
  // For options that re-plan several scenes at once: one row per scene.
  schedule?: Manifest[] | null;
  manifest_hash: string;
  preview_url?: string;
  preview_status: "none" | "rendering" | "ready" | "failed";
}

export interface Decision {
  request_id: string;
  status: DecisionStatus;
  question: string;
  authority: string;
  bound: { script: number; constraints: number };
  opened_at: string;
  expires_at: string;
  candidates: Candidate[];
  answer?: { candidate_id: string; note?: string; answered_by: string; answered_by_name?: string; at: string };
  authority_name?: string;
  // Script supervisor's story requirements, shown as prose for the director (not machine-checked).
  must_keep?: string[];
  requirements_note?: string;
}

export interface Release {
  release_id: string;
  number: number;
  status: ReleaseStatus;
  created_at: string;
  manifest_hash: string;
  summary: string;
  call_sheet_url?: string;
  preview_url?: string;
  duty_changes?: Record<string, string[]>;
  publications: { room: string; room_name?: string; platform: "discord" | "mattermost"; status: PublicationStatus }[];
  acks: {
    expected: string[];
    confirmed: { person: string; at: string; source?: "mattermost" | "discord" }[];
    policy: "affected_only" | "everyone";
  };
}

export interface CrewMember {
  id: string;
  name: string;
  role: string;
  call_time?: string;
  acked_release?: number;
  affected?: boolean;
  role_label?: string;
  // What changed for this person since the release they last confirmed.
  since_confirmed?: string[];
}

export type TimelineKind =
  | "change" | "hold" | "job" | "check" | "render"
  | "decision" | "release" | "ack" | "stale_reply" | "error";

export interface TimelineItem {
  at: string;
  kind: TimelineKind;
  text: string;
  ref?: string;
}

export interface State {
  production: { id: string; title: string; timezone: string; now: string; day: string };
  revisions: { script: number; constraints: number };
  scenes: Scene[];
  changes: Change[];
  jobs: Job[];
  decision: Decision | null;
  releases: Release[];
  crew: CrewMember[];
  timeline: TimelineItem[];
}

export interface ChangeCommand {
  entity: Change["entity"];
  target: string;
  field: string;
  value: string;
  reporter: string;
}
