// Top bar, the headline with its progress beats, the history drawer and the two dialogs.
import { useEffect, useRef, useState, type FormEvent } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowsClockwise, CheckCircle, ClockCounterClockwise, FilmStrip, Gavel, Lightning, Pause,
  PaperPlaneTilt, Plus, Robot, ShieldCheck, Warning, X, type Icon,
} from "@phosphor-icons/react";
import type { ChangeCommand, State, TimelineKind } from "../types";
import { dayLabel, hhmm } from "../format";
import { fixtures, postChange, type Source } from "../data";
import { BEATS, beat, humanize, story } from "../story";
import "./Shell.css";

const EASE = [0.23, 1, 0.32, 1] as const;

export function TopBar({ state, source, setFixture, onHistory, onReport }: {
  state: State; source: Source; setFixture: (i: number) => void; onHistory: () => void; onReport: () => void;
}) {
  const live = source.kind === "live";
  return (
    <header className="topbar">
      <div className="brand">
        <span className="logo" aria-hidden><i /><i /></span>
        <span className="brand-name">Take Two</span>
        <span className="brand-sep" />
        <span className="film">{state.production.title}</span>
        <span className="film-day">{dayLabel(state.production.day)}</span>
      </div>
      <div className="top-actions">
        {source.kind === "fixture" ? (
          <div className="replay" role="group" aria-label="Demo replay">
            <span className="replay-label">Replay</span>
            {fixtures.length <= 9 ? (
              fixtures.map((f, i) => (
                <button key={f.name} aria-pressed={i === source.index} title={f.name} onClick={() => setFixture(i)}>{i + 1}</button>
              ))
            ) : (
              <>
                <button aria-label="Previous moment" onClick={() => setFixture(Math.max(0, source.index - 1))}>‹</button>
                <span className="replay-pos" title={fixtures[source.index]?.name}>{source.index + 1}/{fixtures.length} · {fixtures[source.index]?.name}</span>
                <button aria-label="Next moment" onClick={() => setFixture(Math.min(fixtures.length - 1, source.index + 1))}>›</button>
              </>
            )}
          </div>
        ) : (
          <span className="conn" data-kind={source.kind}>
            <span className="conn-dot" />
            {live ? "Live from Switch" : source.kind === "connecting" ? "Connecting" : "Reconnecting"}
          </span>
        )}
        <span className="clock">{hhmm(state.production.now, state.production.timezone)}</span>
        <button className="btn" onClick={onHistory}><ClockCounterClockwise size={15} /> <span>History</span></button>
        <button className="btn btn-primary" onClick={onReport} disabled={!live} title={live ? undefined : "Connect to the coordinator to report a change"}>
          <Plus size={15} weight="bold" /> <span>Report a change</span>
        </button>
      </div>
    </header>
  );
}

export function Lead({ state }: { state: State }) {
  const s = story(state);
  const b = beat(state);
  return (
    <section className="lead" data-tone={s.tone}>
      <div className="lead-text">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.h1
            key={s.headline}
            initial={{ opacity: 0, y: 10, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -8, filter: "blur(6px)" }}
            transition={{ duration: 0.38, ease: EASE }}
          >
            {s.headline}
          </motion.h1>
        </AnimatePresence>
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.p
            key={s.detail}
            className="lead-detail"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, delay: 0.08 }}
          >
            {s.detail}
          </motion.p>
        </AnimatePresence>
      </div>
      {b && (
        <ol className="beats" aria-label="Progress of the latest change">
          {BEATS.map((name, i) => {
            const n = i + 1;
            const st = n < b.at ? "done" : n === b.at ? (b.redo ? "redo" : "now") : "next";
            return (
              <li key={name} data-state={st}>
                <span className="beat-bar"><motion.span className="beat-fill" initial={false} animate={{ scaleX: st === "done" ? 1 : st === "now" || st === "redo" ? 0.5 : 0 }} transition={{ duration: 0.45, ease: EASE }} /></span>
                <span className="beat-name">{name}</span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}

const KIND_ICON: Record<TimelineKind, Icon> = {
  change: Lightning, hold: Pause, job: Robot, check: ShieldCheck, render: FilmStrip,
  decision: Gavel, release: PaperPlaneTilt, ack: CheckCircle, stale_reply: ArrowsClockwise, error: Warning,
};

export function History({ state, open, onClose }: { state: State; open: boolean; onClose: () => void }) {
  const tz = state.production.timezone;
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="scrim" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} />
          <motion.aside
            className="drawer"
            aria-label="History"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.35, ease: [0.32, 0.72, 0, 1] }}
          >
            <header className="drawer-head">
              <h2>History</h2>
              <button className="icon-btn" onClick={onClose} aria-label="Close history"><X size={16} /></button>
            </header>
            <ol className="events">
              {groupRepeats(state.timeline.map((t) => ({ ...t, text: humanize(state.crew, t.text) }))).map(({ item: t, count }, i) => {
                const I = KIND_ICON[t.kind] ?? Lightning;
                return (
                  <li key={`${t.at}-${i}`} data-kind={t.kind}>
                    <span className="ev-icon"><I size={13} weight="bold" /></span>
                    <span className="ev-time">{hhmm(t.at, tz)}</span>
                    <p>{t.text}{count > 1 && <span className="ev-count">×{count}</span>}</p>
                  </li>
                );
              })}
            </ol>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

// Consecutive identical entries collapse into one line with a count.
function groupRepeats<T extends { text: string; kind: string }>(items: T[]): { item: T; count: number }[] {
  const out: { item: T; count: number }[] = [];
  for (const item of items) {
    const last = out[out.length - 1];
    if (last && last.item.text === item.text && last.item.kind === item.kind) last.count++;
    else out.push({ item, count: 1 });
  }
  return out;
}

function Dialog({ open, onClose, label, children, wide }: { open: boolean; onClose: () => void; label: string; children: React.ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} className={`dialog ${wide ? "dialog-wide" : ""}`} aria-label={label} onClose={onClose} onClick={(e) => e.target === ref.current && onClose()}>
      {open && children}
    </dialog>
  );
}

export function SheetDialog({ url, onClose }: { url: string | null; onClose: () => void }) {
  return (
    <Dialog open={!!url} onClose={onClose} label="Call sheet" wide>
      <div className="dialog-head"><h2>Call sheet</h2><button className="icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button></div>
      {url && <img className="sheet-img" src={url} alt="Call sheet for the current release" />}
    </Dialog>
  );
}

const FIELDS: Record<ChangeCommand["entity"], string[]> = {
  location: ["permission", "window"],
  person: ["hard_stop", "available", "late_by"],
  scene: ["status"],
  capability: ["status"],
};

export function ReportDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [cmd, setCmd] = useState<ChangeCommand>({ entity: "location", target: "", field: "permission", value: "", reporter: "" });
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await postChange(cmd);
      setResult(r.status === "rejected" ? `Rejected: ${r.reason ?? "unknown reason"}` : r.status === "pending_confirmation" ? "Sent. Waiting for the responsible person to confirm." : "Recorded. Affected scenes are held while new options are made.");
      if (r.status !== "rejected") setCmd((c) => ({ ...c, value: "" }));
    } catch {
      setResult("Couldn't reach the coordinator.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={open} onClose={() => { setResult(null); onClose(); }} label="Report a change">
      <form className="report" onSubmit={submit}>
        <div className="dialog-head"><h2>Report a change</h2><button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><X size={16} /></button></div>
        <p className="report-hint">Same as typing <code>/change</code> in the Switch production room.</p>
        <label><span>What changed</span>
          <select value={cmd.entity} onChange={(e) => { const entity = e.target.value as ChangeCommand["entity"]; setCmd((c) => ({ ...c, entity, field: FIELDS[entity][0] })); }}>
            {Object.keys(FIELDS).map((k) => <option key={k}>{k}</option>)}
          </select>
        </label>
        <label><span>Which one</span><input required value={cmd.target} placeholder="rooftop, maya" onChange={(e) => setCmd((c) => ({ ...c, target: e.target.value }))} /></label>
        <label><span>Field</span>
          <select value={cmd.field} onChange={(e) => setCmd((c) => ({ ...c, field: e.target.value }))}>
            {FIELDS[cmd.entity].map((f) => <option key={f}>{f}</option>)}
          </select>
        </label>
        <label><span>New value</span><input required value={cmd.value} placeholder="refused, 18:00" onChange={(e) => setCmd((c) => ({ ...c, value: e.target.value }))} /></label>
        <label><span>Reported by</span><input required value={cmd.reporter} placeholder="nila" onChange={(e) => setCmd((c) => ({ ...c, reporter: e.target.value }))} /></label>
        <button className="btn btn-primary report-send" disabled={busy}>{busy ? "Sending…" : "Send"}</button>
        {result && <p className="report-result" role="status">{result}</p>}
      </form>
    </Dialog>
  );
}
