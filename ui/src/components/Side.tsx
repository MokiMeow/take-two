// Right column: the open question for the director, the current release and the crew.
// The decision card follows Affect UI's Decision Inbox (MIT): a question with its answers,
// folding to one line once it is resolved.
import { AnimatePresence, motion } from "motion/react";
import { ArrowBendUpLeft, Check, Clock, FileText, Warning } from "@phosphor-icons/react";
import type { State } from "../types";
import { hhmm, initials, paperFor } from "../format";
import { currentRelease, humanize, pendingCrew, roleLabel, who as whoOf } from "../story";
import { mediaUrl } from "../data";
import { useMemo } from "react";
import type { Candidate } from "../types";
import { maquette } from "../sets/maquette";
import "../sets/sets.css";
import "./Side.css";

// The option's set model, built from its own manifest.
export function Stage({ c, state, letter, caption }: { c: Candidate; state: State; letter?: string; caption: string }) {
  const tz = state.production.timezone;
  return (
    <div className="stage">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.div key={c.candidate_id} className="stage-model" initial={{ opacity: 0, y: 14, scale: 0.98, filter: "blur(6px)" }} animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }} exit={{ opacity: 0, y: -10, filter: "blur(6px)" }} transition={{ duration: 0.5, ease: EASE }}>
          <SetModel c={c} state={state} />
        </motion.div>
      </AnimatePresence>
      <div className="stage-cap">
        {letter && <i className="letter">{letter}</i>}
        <span className="stage-loc">{c.manifest.location}</span>
        <span className="stage-time">{hhmm(c.manifest.start, tz)}–{hhmm(c.manifest.end, tz)}</span>
        <span className="stage-shots">{c.manifest.shots.join(" · ")}</span>
      </div>
      <span className="stage-tag">{caption}</span>
    </div>
  );
}

function SetModel({ c, state }: { c: Candidate; state: State }) {
  const names = useMemo(() => Object.fromEntries(state.crew.map((m) => [m.id, m.name])), [state.crew]);
  const castKey = c.manifest.people.filter((id) => /actor/i.test(state.crew.find((m) => m.id === id)?.role ?? "")).join(",");
  const shotKey = c.manifest.shots.join(",");
  const location = c.manifest.location;
  // Keyed on joined strings so a fresh array with the same content does not redraw the model.
  const svg = useMemo(
    () => maquette({ location, people: castKey ? castKey.split(",") : [], shots: shotKey ? shotKey.split(",") : [], names }),
    [location, castKey, shotKey, names],
  );
  return <div className="set iso" dangerouslySetInnerHTML={{ __html: svg }} />;
}

const EASE = [0.23, 1, 0.32, 1] as const;
const LETTERS = "ABCDEFGH";

export function ReplanCard({ state }: { state: State }) {
  const held = state.scenes.filter((x) => x.validity === "held");
  const sc = held[held.length - 1];
  const nums = held.map((x) => x.number).join(" and ");
  const agents = [
    { role: "script-supervisor", name: "Claude Code", job: "What must each scene keep?" },
    { role: "first-ad", name: "Codex", job: "Plans that fit the new facts" },
  ];
  const status = (role: string) => {
    const j = [...state.jobs].reverse().find((x) => x.role === role);
    return j?.status === "done" ? "done" : j ? "working" : "queued";
  };
  return (
    <motion.section layout className="card decision replan" transition={{ duration: 0.3, ease: EASE }}>
      <header className="card-head"><span className="dot dot-ask" /> Re-planning Scene{held.length > 1 ? "s" : ""} {nums}</header>
      {sc?.plan && (
        <div className="replan-stage">
          <Stage c={{ candidate_id: `held-${sc.id}`, label: sc.title, story_cost: "", check: { result: "pass", reasons: [] }, manifest_hash: "", preview_status: "none",
            manifest: { scene_id: sc.id, location: sc.plan.location, start: sc.plan.start, end: sc.plan.end, setup_min: sc.plan.setup_min, wrap_min: sc.plan.wrap_min, people: sc.plan.people, shots: ["wide"], capabilities: [] } }}
            state={state} caption={`On hold · the plan nobody may use`} />
          <span className="replan-hold">On hold</span>
        </div>
      )}
      <ul className="agents">
        {agents.map((a) => (
          <li key={a.role} data-status={status(a.role)}>
            <span className="agent-dot" />
            <b>{a.name}</b><small>{a.role}</small>
            <span className="agent-job">{a.job}</span>
          </li>
        ))}
      </ul>
      <p className="how">The agents only propose. Every plan is checked in code before {state.decision?.authority_name ?? "the director"} sees it.</p>
    </motion.section>
  );
}

export function DecisionCard({ state, focus, onFocus }: { state: State; focus: string | null; onFocus: (id: string | null) => void }) {
  const d = state.decision;
  const tz = state.production.timezone;
  if (!d) return null;
  if (d.status === "answered" && state.scenes.some((x) => x.validity === "held")) return <ReplanCard state={state} />;
  const passing = d.candidates.filter((c) => c.check.result === "pass");
  const ruled = d.candidates.filter((c) => c.check.result !== "pass");
  const chosen = d.answer && d.candidates.find((c) => c.candidate_id === d.answer!.candidate_id);
  const sceneId = d.candidates[0]?.manifest.scene_id;
  const who = d.authority_name ?? whoOf(state.crew, d.authority);

  return (
    <motion.section layout className="card decision" data-status={d.status} transition={{ duration: 0.3, ease: EASE }}>
      <header className="card-head">
        {d.status === "open" && <><span className="dot dot-ask" /> Needs {who}</>}
        {d.status === "closed_outdated" && <><Warning size={14} weight="bold" className="t-stop" /> Question closed: facts changed</>}
        {d.status === "answered" && <><Check size={14} weight="bold" className="t-go" /> Decided</>}
        {(d.status === "expired" || d.status === "rejected_unauthorized") && <>Question {d.status.replace("_", " ")}</>}
        {d.status === "open" && <span className="card-meta"><Clock size={12} /> by {hhmm(d.expires_at, tz)}</span>}
      </header>

      <AnimatePresence mode="popLayout" initial={false}>
        {d.status === "answered" && chosen ? (
          <motion.div key="answered" className="answer" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.28, ease: EASE }}>
            <Stage c={chosen} state={state} caption="Set model · the approved plan" />
            <p className="answer-line">{d.answer!.answered_by_name ?? whoOf(state.crew, d.answer!.answered_by)} chose <b>{chosen.label}</b>.</p>
            {d.answer!.note && <blockquote>“{d.answer!.note}”</blockquote>}
            <p className="answer-meta">{hhmm(d.answer!.at, tz)} · answered in Switch</p>
          </motion.div>
        ) : (
          <motion.div key="open" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.22 }}>
            {passing.length > 0 && (() => {
              const fi = Math.max(0, passing.findIndex((c) => focus === `${sceneId}:${c.candidate_id}`));
              return <Stage c={passing[fi]} state={state} letter={LETTERS[fi]} caption={`Set model · option ${LETTERS[fi]}`} />;
            })()}
            <p className="question">{d.question}</p>
            {d.must_keep && d.must_keep.length > 0 && (
              <p className="must-keep" title={d.requirements_note}>
                <span>Story must keep</span> {d.must_keep.join("; ")}
              </p>
            )}
            <ul className="choices" data-stale={d.status === "closed_outdated"}>
              {passing.map((c, i) => (
                <motion.li
                  key={c.candidate_id}
                  data-focus={focus === `${sceneId}:${c.candidate_id}`}
                  onMouseEnter={() => onFocus(`${sceneId}:${c.candidate_id}`)}
                  onMouseLeave={() => onFocus(null)}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.06 * i, duration: 0.24, ease: EASE }}
                >
                  <i className="letter">{LETTERS[i]}</i>
                  <div>
                    <p className="choice-title">{c.label} <span className="choice-time">{hhmm(c.manifest.start, tz)}–{hhmm(c.manifest.end, tz)}</span></p>
                    <p className="choice-cost">{c.story_cost}</p>
                  </div>
                </motion.li>
              ))}
            </ul>
            {ruled.length > 0 && (
              <p className="ruled"><span>{ruled.length} ruled out by the checker:</span> {ruled.map((c) => `${c.label}: ${c.check.reasons[0] ?? "fails a check"}`).join(" · ")}</p>
            )}
            {d.status === "closed_outdated" && <p className="how t-stop">Nobody can pick these now. New options are on the way.</p>}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}

export function ReleaseCard({ state, onSheet }: { state: State; onSheet: (url: string) => void }) {
  const r = currentRelease(state);
  const tz = state.production.timezone;
  if (!r) return null;
  const sheet = mediaUrl(r.call_sheet_url);
  return (
    <motion.section layout className="card release" transition={{ duration: 0.3, ease: EASE }}>
      <header className="card-head">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span key={r.number} className="rel-num" initial={{ opacity: 0, filter: "blur(4px)", y: 6 }} animate={{ opacity: 1, filter: "blur(0px)", y: 0 }} exit={{ opacity: 0, filter: "blur(4px)", y: -6 }} transition={{ duration: 0.3, ease: EASE }}>
            Release {r.number}
          </motion.span>
        </AnimatePresence>
        <span className="card-meta">{hhmm(r.created_at, tz)} · through Switch</span>
      </header>
      <div className="rel-body">
        {sheet && (
          <button className="rel-sheet" onClick={() => onSheet(sheet)} aria-label="Open the call sheet" style={{ background: paperFor(r.number).bg }}>
            <img src={sheet} alt="" />
          </button>
        )}
        <div className="rel-text">
          <p className="rel-summary">{r.summary}</p>
          <ul className="rel-rooms">
            {r.publications.map((p) => (
              <li key={p.room} data-platform={p.platform} data-status={p.status}>
                <span className="rel-room-icon" />{p.room_name ?? roomsOf([p])}<small>{p.platform === "discord" ? "Discord" : "Mattermost"}</small>
                {p.status === "sent" && <Check size={11} weight="bold" className="t-go" />}
              </li>
            ))}
          </ul>
          {sheet && <button className="ghost-btn" onClick={() => onSheet(sheet)}><FileText size={14} /> Call sheet · {paperFor(r.number).name} paper</button>}
        </div>
      </div>
    </motion.section>
  );
}

// Room names as people know them; a bare room id falls back to its platform.
function roomsOf(pubs: { room: string; room_name?: string; platform: string }[]): string {
  const names = pubs.map((p) => p.room_name ?? (/^[0-9a-f-]{20,}$/i.test(p.room) ? (p.platform === "discord" ? "Discord" : "production room") : p.room));
  return [...new Set(names)].join(", ") || "nobody yet";
}

// Drop lines that restate an unchanged value, such as "Call 14:45 (was 14:45)".
function isRealChange(line: string): boolean {
  const m = /(\d\d:\d\d) \(was (\d\d:\d\d)\)/.exec(line);
  return !(m && m[1] === m[2]);
}

// Crew messages waiting for the responsible person to record or ignore them.
export function PendingCard({ state }: { state: State }) {
  const pending = state.changes.filter((c) => c.status === "pending_confirmation" && !c.resolution).slice(0, 3);
  if (!pending.length) return null;
  return (
    <motion.section layout className="card pending" transition={{ duration: 0.3, ease: EASE }}>
      <header className="card-head"><span className="dot dot-ask" /> Waiting on a person</header>
      <ul className="reports">
        {pending.map((c) => (
          <li key={c.id}>
            <p><b>{c.reporter_name ?? whoOf(state.crew, c.reporter)}</b> said “{c.value}”</p>
            <small>A proposed change waits for the responsible person to record it. Nothing changes until they do.</small>
          </li>
        ))}
      </ul>
    </motion.section>
  );
}

export function CrewCard({ state }: { state: State }) {
  const r = currentRelease(state);
  const tz = state.production.timezone;
  const waiting = new Set(pendingCrew(state).map((c) => c.id));
  const stale = [...state.timeline].reverse().find((t) => t.kind === "stale_reply");
  const confirmed = r ? r.acks.confirmed.length : 0;
  return (
    <motion.section layout className="card crew" transition={{ duration: 0.3, ease: EASE }}>
      <header className="card-head">
        Crew
        {r && (
          <span className="card-meta">
            {r.acks.expected.length ? `${confirmed} of ${r.acks.expected.length} confirmed release ${r.number}` : `no call times changed in release ${r.number}`}
          </span>
        )}
      </header>
      <ul className="people">
        {state.crew.map((c) => {
          const ok = r?.acks.confirmed.find((a) => a.person === c.id);
          const late = waiting.has(c.id);
          return (
            <li key={c.id}>
              <span className="avatar">{initials(c.name)}</span>
              <div className="person">
                <p>{c.name}</p>
                <small>{c.role_label ?? roleLabel(c.role)}</small>
              </div>
              <span className="call">{c.call_time ? hhmm(c.call_time, tz) : "--:--"}</span>
              <AnimatePresence mode="popLayout" initial={false}>
                <motion.span
                  key={ok ? `ok${r!.number}` : late ? "late" : c.acked_release ? `carry${c.acked_release}` : "none"}
                  className="state"
                  data-tone={ok ? "go" : late ? "hold" : c.acked_release ? "carry" : "none"}
                  title={!ok && !late && c.acked_release ? "Their call time did not change, so their earlier confirmation still holds." : undefined}
                  initial={{ opacity: 0, scale: 0.6, filter: "blur(4px)" }}
                  animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                  exit={{ opacity: 0, scale: 0.6, filter: "blur(4px)" }}
                  transition={{ type: "spring", duration: 0.3, bounce: 0 }}
                >
                  {ok ? <><Check size={11} weight="bold" /> r{r!.number}</> : late ? (c.acked_release ? `on r${c.acked_release}` : "waiting") : c.acked_release ? <><Check size={11} weight="bold" /> r{c.acked_release}</> : "—"}
                </motion.span>
              </AnimatePresence>
              {late && c.since_confirmed && c.since_confirmed.length > 0 && (
                <ul className="since" title={c.since_confirmed.join(" · ")}>
                  {c.since_confirmed.filter(isRealChange).slice(0, 3).map((l) => <li key={l}>{l.replace(/_/g, " ")}</li>)}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
      <AnimatePresence initial={false}>
        {stale && (
          <motion.p key={stale.at} className="stale" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.3, ease: EASE }}>
            <ArrowBendUpLeft size={13} weight="bold" /> {humanize(state.crew, stale.text)}
          </motion.p>
        )}
      </AnimatePresence>
    </motion.section>
  );
}
