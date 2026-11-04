// Right column: the open question for the director, the current release and the crew.
// The decision card follows Affect UI's Decision Inbox (MIT): a question with its answers,
// folding to one line once it is resolved.
import { AnimatePresence, motion } from "motion/react";
import { ArrowBendUpLeft, Check, Clock, FileText, Warning } from "@phosphor-icons/react";
import type { State } from "../types";
import { hhmm, initials } from "../format";
import { currentRelease, humanize, pendingCrew, roleLabel, who as whoOf } from "../story";
import { mediaUrl } from "../data";
import { useMemo } from "react";
import type { Candidate } from "../types";
import { maquette } from "../sets/maquette";
import "../sets/sets.css";
import "./Side.css";

// The option's set model, built from its own manifest.
function SetModel({ c, state }: { c: Candidate; state: State }) {
  const names = useMemo(() => Object.fromEntries(state.crew.map((m) => [m.id, m.name])), [state.crew]);
  const cast = c.manifest.people.filter((id) => /actor/i.test(state.crew.find((m) => m.id === id)?.role ?? ""));
  const svg = useMemo(
    () => maquette({ location: c.manifest.location, people: cast, shots: c.manifest.shots, names }),
    [c.manifest.location, cast.join(","), c.manifest.shots.join(","), names],
  );
  return <div className="set iso" dangerouslySetInnerHTML={{ __html: svg }} />;
}

const EASE = [0.23, 1, 0.32, 1] as const;
const LETTERS = "ABCDEFGH";

export function DecisionCard({ state, focus, onFocus }: { state: State; focus: string | null; onFocus: (id: string | null) => void }) {
  const d = state.decision;
  const tz = state.production.timezone;
  if (!d) return null;
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
            <SetModel c={chosen} state={state} />
            <p className="answer-line">{d.answer!.answered_by_name ?? whoOf(state.crew, d.answer!.answered_by)} chose <b>{chosen.label}</b>.</p>
            {d.answer!.note && <blockquote>“{d.answer!.note}”</blockquote>}
            <p className="answer-meta">{hhmm(d.answer!.at, tz)} · answered in Switch</p>
          </motion.div>
        ) : (
          <motion.div key="open" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.22 }}>
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
                  <SetModel c={c} state={state} />
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
        <span className="card-meta">{hhmm(r.created_at, tz)} · sent to {roomsOf(r.publications)}</span>
      </header>
      <p className="rel-summary">{r.summary}</p>
      {sheet && (
        <button className="ghost-btn" onClick={() => onSheet(sheet)}>
          <FileText size={14} /> Call sheet
        </button>
      )}
    </motion.section>
  );
}

// Room names as people know them; a bare room id falls back to its platform.
function roomsOf(pubs: { room: string; room_name?: string; platform: string }[]): string {
  const names = pubs.map((p) => p.room_name ?? (/^[0-9a-f-]{20,}$/i.test(p.room) ? (p.platform === "discord" ? "Discord" : "production room") : p.room));
  return [...new Set(names)].join(", ") || "nobody yet";
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
