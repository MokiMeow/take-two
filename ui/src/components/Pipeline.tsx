import { motion, useReducedMotion } from "motion/react";
import type { State } from "../types";
import { hhmm, title } from "../format";
import { StatusDot, type DotState } from "./bits";
import "./Pipeline.css";

interface Step {
  key: string;
  label: string;
  state: DotState;
  detail: string;
}

// Turns the coordinator's state into the seven visible steps of the change loop.
// Display only: every status here is read from fields the coordinator already decided.
export function deriveSteps(s: State): Step[] {
  const change = s.changes[0];
  const latest = s.releases[0];
  const tz = s.production.timezone;
  const releasedAfterChange = !!(change && latest && latest.created_at > change.at);
  const sup = s.jobs.find((j) => j.role === "script-supervisor");
  const ad = s.jobs.find((j) => j.role === "first-ad");
  const held = s.scenes.filter((x) => x.validity !== "valid");
  const d = s.decision;
  const fresh = d && change ? d.bound.constraints === s.revisions.constraints : !!d;

  const jobState = (j?: (typeof s.jobs)[number]): DotState =>
    !j ? "idle" : j.status === "done" ? "done" : j.status === "failed" ? "failed" : j.status === "cancelled" ? "cancelled" : j.status === "running" ? "running" : "queued";

  const passing = d?.candidates.filter((c) => c.check.result === "pass").length ?? 0;
  const failing = d?.candidates.filter((c) => c.check.result === "fail").length ?? 0;
  const verify = d?.candidates.filter((c) => c.check.result === "needs_verification").length ?? 0;

  let decideState: DotState = "idle";
  let decideDetail = "No decision needed";
  if (d && fresh) {
    if (d.status === "open") { decideState = "running"; decideDetail = `Waiting for ${d.authority}`; }
    else if (d.status === "answered") { decideState = "done"; decideDetail = `Answered ${hhmm(d.answer?.at, tz)}`; }
    else if (d.status === "expired") { decideState = "hold"; decideDetail = "Expired — nothing picked"; }
    else if (d.status === "rejected_unauthorized") { decideState = "failed"; decideDetail = "Wrong person answered — re-asked"; }
  } else if (d && d.status === "closed_outdated") {
    decideState = "cancelled"; decideDetail = `r${d.bound.constraints} question closed — outdated`;
  }

  const acked = latest ? latest.acks.confirmed.length : 0;
  const expected = latest ? latest.acks.expected.length : 0;

  return [
    {
      key: "record", label: "Record",
      state: change ? (change.status === "pending_confirmation" ? "hold" : change.status === "rejected" ? "failed" : "done") : "idle",
      detail: change ? `${title(change.target)} ${change.field.replace(/_/g, " ")}: ${/^\d{4}-\d\d-\d\dT/.test(change.value) ? hhmm(change.value, tz) : change.value}` : "No changes",
    },
    {
      key: "hold", label: "Hold",
      state: held.length ? "hold" : change ? "done" : "idle",
      detail: held.length ? `Scene ${held.map((h) => h.number).join(", ")} on hold` : change ? "Hold lifted" : "—",
    },
    { key: "sup", label: "Script Supervisor", state: jobState(sup), detail: sup?.summary ?? (sup ? "Thinking…" : "—") },
    { key: "ad", label: "1st AD", state: jobState(ad), detail: ad?.summary ?? (ad ? "Finding options…" : "—") },
    {
      key: "check", label: "Check",
      state: d && fresh ? (verify ? "verify" : passing ? "done" : "failed") : "idle",
      detail: d && fresh ? `${passing} pass · ${failing} ruled out${verify ? ` · ${verify} to verify` : ""}` : "—",
    },
    { key: "decide", label: "Decide", state: decideState, detail: decideDetail },
    {
      key: "release", label: "Release",
      state: releasedAfterChange || !change ? (latest ? "done" : "idle") : "idle",
      detail: latest && (releasedAfterChange || !change) ? `Release ${latest.number} published` : "—",
    },
    {
      key: "confirm", label: "Confirm",
      state: latest && (releasedAfterChange || !change) ? (acked >= expected ? "done" : "running") : "idle",
      detail: latest && (releasedAfterChange || !change) ? `${acked} of ${expected} on r${latest.number}` : "—",
    },
  ];
}

export function Pipeline({ state }: { state: State }) {
  const reduce = useReducedMotion();
  const steps = deriveSteps(state);
  const activeIdx = steps.reduce((acc, st, i) => (st.state !== "idle" ? i : acc), -1);

  return (
    <ol className="pipeline" aria-label="Change loop">
      <div className="pipeline-rail" aria-hidden>
        <motion.div
          className="pipeline-rail-fill"
          initial={false}
          animate={{ scaleX: activeIdx < 0 ? 0 : activeIdx / (steps.length - 1) }}
          transition={reduce ? { duration: 0 } : { duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
      {steps.map((st) => (
        <li key={st.key} className={`step step-${st.state}`}>
          <div className="step-dot">
            <StatusDot state={st.state} size={10} />
          </div>
          <div className="step-label">{st.label}</div>
          <div className="step-detail" title={st.detail}>{st.detail}</div>
        </li>
      ))}
    </ol>
  );
}
