import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useState, type FormEvent } from "react";
import {
  ArrowsClockwise, CheckCircle, FilmStrip, Gavel, Lightning, Pause, PaperPlaneTilt,
  Plus, Robot, ShieldCheck, Warning, X, type Icon,
} from "@phosphor-icons/react";
import type { ChangeCommand, State, TimelineItem, TimelineKind } from "../types";
import { hhmm } from "../format";
import { fixtures, postChange, type Source } from "../data";
import { Section, Slate, StatusDot } from "./bits";
import "./Chrome.css";

export function TopBar({ state, source, setFixture }: { state: State; source: Source; setFixture: (i: number) => void }) {
  const take = state.releases[0]?.number ?? 0;
  return (
    <header className="topbar">
      <div className="topbar-left">
        <Slate take={take} />
        <div className="topbar-title">
          <span className="serif topbar-film">{state.production.title}</span>
          <span className="mono faint topbar-day">{state.production.day}</span>
        </div>
      </div>
      <div className="topbar-right">
        <span className="rev mono"><span className="faint">script</span> r{state.revisions.script}</span>
        <span className="rev mono"><span className="faint">facts</span> r{state.revisions.constraints}</span>
        <span className="clock mono">{hhmm(state.production.now, state.production.timezone)} <span className="faint">IST</span></span>
        <SourceBadge source={source} setFixture={setFixture} />
      </div>
    </header>
  );
}

function SourceBadge({ source, setFixture }: { source: Source; setFixture: (i: number) => void }) {
  if (source.kind === "fixture") {
    return (
      <div className="source source-fixture" role="group" aria-label="Fixture replay">
        <span className="mono">Fixture replay</span>
        {fixtures.map((f, i) => (
          <button key={f.name} className={`fx ${i === source.index ? "on" : ""}`} onClick={() => setFixture(i)} title={f.name} aria-pressed={i === source.index}>
            {i + 1}
          </button>
        ))}
      </div>
    );
  }
  const map = { live: ["done", "Live · Switch"], connecting: ["queued", "Connecting"], reconnecting: ["hold", "Reconnecting"] } as const;
  const [dot, label] = map[source.kind];
  return (
    <span className="source">
      <StatusDot state={dot} size={7} />
      <span className="mono">{label}</span>
    </span>
  );
}

const KIND_ICON: Record<TimelineKind, Icon> = {
  change: Lightning, hold: Pause, job: Robot, check: ShieldCheck, render: FilmStrip,
  decision: Gavel, release: PaperPlaneTilt, ack: CheckCircle, stale_reply: ArrowsClockwise, error: Warning,
};

export function Timeline({ items, tz }: { items: TimelineItem[]; tz: string }) {
  const reduce = useReducedMotion();
  return (
    <Section label="Timeline" className="timeline-section">
      <ol className="timeline">
        <AnimatePresence initial={false}>
          {items.slice(0, 40).map((it) => {
            const I = KIND_ICON[it.kind] ?? Lightning;
            return (
              <motion.li
                key={it.at + it.kind + it.text}
                layout={!reduce}
                className={`tl tl-${it.kind}`}
                initial={reduce ? false : { opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              >
                <span className="tl-time mono">{hhmm(it.at, tz)}</span>
                <span className="tl-icon"><I size={13} /></span>
                <span className="tl-text">{it.text}</span>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ol>
    </Section>
  );
}

const FIELDS: Record<ChangeCommand["entity"], string[]> = {
  location: ["permission", "window"],
  person: ["hard_stop", "available", "late_by"],
  scene: ["status"],
  capability: ["status"],
};

export function ReportChange({ disabled }: { disabled: boolean }) {
  const [open, setOpen] = useState(false);
  const [cmd, setCmd] = useState<ChangeCommand>({ entity: "location", target: "", field: "permission", value: "", reporter: "" });
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await postChange(cmd);
      setResult(r.status === "rejected" ? `Rejected: ${r.reason ?? "unknown reason"}` : r.status === "pending_confirmation" ? "Sent — waiting for the responsible person to confirm." : "Recorded. The loop has started.");
      if (r.status !== "rejected") setCmd((c) => ({ ...c, value: "" }));
    } catch {
      setResult("Couldn't reach the coordinator.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="report">
      <button className="report-btn" onClick={() => { setOpen((v) => !v); setResult(null); }} disabled={disabled} title={disabled ? "Connect to the coordinator to report changes" : "Report a change"}>
        {open ? <X size={14} /> : <Plus size={14} />}
        <span>Report a change</span>
      </button>
      <AnimatePresence>
        {open && (
          <motion.form
            className="report-form"
            onSubmit={submit}
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
          >
            <p className="report-hint">Same as typing <code className="mono">/change</code> in the production room. Goes through the full loop.</p>
            <label><span>What</span>
              <select value={cmd.entity} onChange={(e) => { const entity = e.target.value as ChangeCommand["entity"]; setCmd((c) => ({ ...c, entity, field: FIELDS[entity][0] })); }}>
                {Object.keys(FIELDS).map((k) => <option key={k}>{k}</option>)}
              </select>
            </label>
            <label><span>Which</span><input required value={cmd.target} placeholder="rooftop, maya…" onChange={(e) => setCmd((c) => ({ ...c, target: e.target.value }))} /></label>
            <label><span>Field</span>
              <select value={cmd.field} onChange={(e) => setCmd((c) => ({ ...c, field: e.target.value }))}>
                {FIELDS[cmd.entity].map((f) => <option key={f}>{f}</option>)}
              </select>
            </label>
            <label><span>Value</span><input required value={cmd.value} placeholder="refused, 18:00…" onChange={(e) => setCmd((c) => ({ ...c, value: e.target.value }))} /></label>
            <label><span>Reported by</span><input required value={cmd.reporter} placeholder="nila" onChange={(e) => setCmd((c) => ({ ...c, reporter: e.target.value }))} /></label>
            <button className="report-send" disabled={busy}>{busy ? "Sending…" : "Send"}</button>
            {result && <p className="report-result" role="status">{result}</p>}
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
}
