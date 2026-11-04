import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState } from "react";
import { CaretDown, ChatCircleText, Clock, FilmSlate, UsersThree, Warning } from "@phosphor-icons/react";
import type { Candidate, CrewMember, Decision as DecisionT, State } from "../types";
import { hhmm, minutesBetween, shortHash, span, title } from "../format";
import { mediaUrl } from "../data";
import { Pill, Stamp } from "./bits";
import "./Decision.css";

function fmtLeft(m: number): string {
  const h = Math.floor(m / 60), r = m % 60;
  return h ? (r ? `${h}h ${r}m` : `${h}h`) : `${r}m`;
}

export function Headline({ state }: { state: State }) {
  const d = state.decision;
  const held = state.scenes.filter((s) => s.validity !== "valid");
  const tz = state.production.timezone;
  const latest = state.releases[0];
  const outdated = d?.status === "closed_outdated";

  let kicker = "All clear";
  let line = latest ? `Everyone is working from release ${latest.number}.` : "No plan released yet.";
  let sub: string | undefined = latest?.summary;
  let tone: "calm" | "hold" | "ask" | "done" = "calm";

  if (d?.status === "open" && d.bound.constraints === state.revisions.constraints) {
    kicker = "Decision needed"; tone = "ask";
    line = d.question;
    const left = minutesBetween(state.production.now, d.expires_at);
    sub = `${d.authority} answers in Mattermost · expires ${hhmm(d.expires_at, tz)}${left > 0 ? ` (in ${fmtLeft(left)})` : ""}. Silence picks nothing.`;
  } else if (outdated && held.length) {
    kicker = "Plans changed again"; tone = "hold";
    line = "That question is outdated.";
    sub = `It was asked on constraints r${d!.bound.constraints}; the facts are now r${state.revisions.constraints}. New options are on the way.`;
  } else if (held.length) {
    kicker = "On hold"; tone = "hold";
    line = `Scene ${held.map((h) => h.number).join(" & ")} is on hold.`;
    sub = held[0].hold_reason;
  } else if (d?.status === "answered" && d.answer) {
    const chosen = d.candidates.find((c) => c.candidate_id === d.answer!.candidate_id);
    kicker = "Decided"; tone = "done";
    line = chosen ? `${chosen.label}.` : "Director asked for new options.";
    sub = latest ? `Release ${latest.number}: ${latest.summary}` : undefined;
  }

  return (
    <div className={`headline headline-${tone}`}>
      <span className="eyebrow headline-kicker">{kicker}</span>
      <AnimatePresence mode="wait" initial={false}>
        <motion.h1
          key={line}
          className="serif headline-line"
          initial={{ opacity: 0, y: 8, filter: "blur(4px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          exit={{ opacity: 0, y: -6, filter: "blur(4px)" }}
          transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
        >
          {line}
        </motion.h1>
      </AnimatePresence>
      {sub && <p className="headline-sub">{sub}</p>}
      {d?.status === "answered" && d.answer?.note && !held.length && (
        <p className="headline-note script">
          <ChatCircleText size={14} weight="regular" /> “{d.answer.note}” — {title(d.answer.answered_by)}
        </p>
      )}
    </div>
  );
}

export function DecisionPanel({ decision, crew, current, tz }: { decision: DecisionT; crew: CrewMember[]; current: number; tz: string }) {
  const [showRuledOut, setShowRuledOut] = useState(false);
  const outdated = decision.status === "closed_outdated" || decision.bound.constraints !== current;
  const viable = decision.candidates.filter((c) => c.check.result !== "fail");
  const ruledOut = decision.candidates.filter((c) => c.check.result === "fail");
  const chosenId = decision.status === "answered" ? decision.answer?.candidate_id : undefined;

  return (
    <div className={`decision ${outdated ? "is-outdated" : ""}`}>
      <div className="decision-meta">
        <span className="mono faint">{decision.request_id}</span>
        <span className="mono faint">bound to script r{decision.bound.script} · constraints r{decision.bound.constraints}</span>
        {decision.status === "open" && !outdated && <Pill tone="run">Open in Mattermost</Pill>}
        {decision.status === "answered" && <Pill tone="pass">Answered by {title(decision.answer?.answered_by ?? "")}</Pill>}
        {decision.status === "expired" && <Pill tone="hold">Expired — nothing picked</Pill>}
        {decision.status === "rejected_unauthorized" && <Pill tone="fail">Answer from wrong person ignored</Pill>}
      </div>

      <div className="candidates" data-count={viable.length}>
        {viable.map((c, i) => (
          <CandidateCard
            key={c.candidate_id}
            c={c}
            letter={String.fromCharCode(65 + i)}
            crew={crew}
            tz={tz}
            chosen={chosenId === c.candidate_id}
            dimmed={!!chosenId && chosenId !== c.candidate_id}
          />
        ))}
        <AnimatePresence>
          {outdated && (
            <motion.div className="outdated-veil" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Stamp tone="hold" size="lg" rotate={-8}>Outdated · r{decision.bound.constraints}</Stamp>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {ruledOut.length > 0 && (
        <div className="ruled-out">
          <button className="ruled-out-toggle" onClick={() => setShowRuledOut((v) => !v)} aria-expanded={showRuledOut}>
            <Warning size={14} />
            <span>{ruledOut.length} option{ruledOut.length > 1 ? "s" : ""} ruled out by the checker — never shown to the director</span>
            <CaretDown size={12} className={showRuledOut ? "rot" : ""} />
          </button>
          <AnimatePresence initial={false}>
            {showRuledOut && (
              <motion.ul
                className="ruled-out-list"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              >
                {ruledOut.map((c) => (
                  <li key={c.candidate_id}>
                    <span className="ruled-out-label">{c.label}</span>
                    <span className="mono faint">{span(c.manifest.start, c.manifest.end, tz)}</span>
                    {c.check.reasons.map((r) => (
                      <span key={r} className="ruled-out-reason">{r}</span>
                    ))}
                  </li>
                ))}
              </motion.ul>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

function CandidateCard({ c, letter, crew, tz, chosen, dimmed }: { c: Candidate; letter: string; crew: CrewMember[]; tz: string; chosen: boolean; dimmed: boolean }) {
  const reduce = useReducedMotion();
  const m = c.manifest;
  const names = m.people.map((p) => crew.find((x) => x.id === p)?.name ?? title(p));
  const verify = c.check.result === "needs_verification";

  return (
    <motion.article
      layout={!reduce}
      className={`cand ${chosen ? "is-chosen" : ""} ${dimmed ? "is-dimmed" : ""}`}
      initial={reduce ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: dimmed ? 0.5 : 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
    >
      <Preview c={c} letter={letter} />
      <div className="cand-body">
        <div className="cand-title-row">
          <h3 className="cand-title">{c.label}</h3>
          {chosen ? <Stamp tone="pass" size="sm" rotate={-3}>Chosen</Stamp> : verify ? <Pill tone="verify">Needs a human check</Pill> : <Pill tone="pass">Checks pass</Pill>}
        </div>
        <p className="cand-cost script">{c.story_cost}</p>
        {verify && c.check.reasons.map((r) => <p key={r} className="cand-verify">{r}</p>)}
        <dl className="cand-facts">
          <div><dt><Clock size={13} /></dt><dd className="mono">{span(m.start, m.end, tz)} <span className="faint">· setup {m.setup_min}m · wrap {m.wrap_min}m</span></dd></div>
          <div><dt><FilmSlate size={13} /></dt><dd>{m.shots.map(title).join(" · ")}</dd></div>
          <div><dt><UsersThree size={13} /></dt><dd>{names.join(", ")}</dd></div>
        </dl>
        <div className="cand-hash mono faint" title={c.manifest_hash}>manifest {shortHash(c.manifest_hash)}</div>
      </div>
    </motion.article>
  );
}

function Preview({ c, letter }: { c: Candidate; letter: string }) {
  const [broken, setBroken] = useState(false);
  const src = mediaUrl(c.preview_url);
  const ready = c.preview_status === "ready" && src && !broken;
  return (
    <div className="preview">
      {ready ? (
        <video src={src} autoPlay muted loop playsInline onError={() => setBroken(true)} />
      ) : (
        <div className={`preview-empty ${c.preview_status === "rendering" ? "is-rendering" : ""}`}>
          <span className="mono">
            {c.preview_status === "rendering" ? "Rendering preview…" : c.preview_status === "failed" ? "Preview failed — text only" : broken ? "Preview file missing" : "No preview"}
          </span>
        </div>
      )}
      <span className="preview-letter mono">{letter}</span>
      <span className="preview-loc mono">{c.manifest.location.toUpperCase()}</span>
    </div>
  );
}
