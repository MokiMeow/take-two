/*
 * The day's schedule board. Layout and motion adapted from Subframe Motion's
 * "Schedule ripple" (https://www.subframe.com/motion/schedule-ripple):
 *
 * MIT License · Copyright (c) 2026 Subframe
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software
 * and associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions: The above copyright notice and this
 * permission notice shall be included in all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
 *
 * Each block spans the whole track and is placed with translateX(start%) while its face is sized
 * with scaleX(duration), so every move is a transform.
 */
import type { CSSProperties } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { Candidate, Scene, ScenePlan, State } from "../types";
import { hhmm, title } from "../format";
import { clash, dayWindow, marks, type Mark } from "../story";
import "./Schedule.css";

// Scene colours, in order of scene number.
export const SCENE_COLORS = ["#ff7049", "#bfcaf2", "#c1ccae", "#eee9dd", "#9eafbb", "#f1b84c"];
export const sceneColor = (n: number) => SCENE_COLORS[(n - 1) % SCENE_COLORS.length];

const LETTERS = "ABCDEFGH";

interface Props {
  state: State;
  ghosts: Record<string, ScenePlan>;
  focus: string | null;
  onFocus: (id: string | null) => void;
}

export function Schedule({ state, ghosts, focus, onFocus }: Props) {
  const tz = state.production.timezone;
  const { from, to } = dayWindow(state);
  const span = to - from;
  const pos = (iso: string) => ((+new Date(iso) - from) / span) * 100;
  const frac = (a: string, b: string) => (+new Date(b) - +new Date(a)) / span;
  const hours = Array.from({ length: Math.round(span / 3600_000) + 1 }, (_, i) => from + i * 3600_000);
  const m = marks(state);
  const d = state.decision;
  const showOptions = d && (d.status === "open" || d.status === "closed_outdated");
  const passing = d?.candidates.filter((c) => c.check.result === "pass") ?? [];
  const ruled = d?.candidates.filter((c) => c.check.result !== "pass") ?? [];
  const valid = state.scenes.filter((s) => s.validity === "valid" && s.plan);
  const wrap = valid.length ? valid.reduce((a, s) => (s.plan!.end > a ? s.plan!.end : a), valid[0].plan!.end) : undefined;
  const heldCount = state.scenes.filter((x) => x.validity === "held").length;
  const call = state.crew.map((c) => c.call_time).filter(Boolean).sort()[0];

  return (
    <section className="sheet" aria-label="Today's schedule">
      <header className="sheet-head">
        <h2>Day 1 schedule</h2>
        <span className="sheet-sub">{state.scenes.length} scenes · times in {tz.split("/")[1]}</span>
      </header>

      <div className="sheet-grid" style={{ "--hour": `${100 / Math.max(1, hours.length - 1)}%` } as CSSProperties}>
        <div className="sheet-hours" aria-hidden>
          {hours.map((h) => (
            <span key={h} style={{ left: `${((h - from) / span) * 100}%` }}>{hhmm(new Date(h).toISOString(), tz)}</span>
          ))}
        </div>

        <div className="sheet-rows">
          {state.scenes.map((s) => (
            <div key={s.id}>
              <SceneRow scene={s} ghost={ghosts[s.id]} pos={pos} frac={frac} tz={tz} marks={m} dim={!!focus && !focus.startsWith(s.id)} />
              <AnimatePresence initial={false}>
                {showOptions && d!.candidates[0]?.manifest.scene_id === s.id && (
                  <motion.div
                    className="opts"
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.32, ease: [0.23, 1, 0.32, 1] }}
                  >
                    {[...passing, ...ruled].map((c, i) => (
                      <OptionRow
                        key={c.candidate_id}
                        c={c}
                        letter={c.check.result === "pass" ? LETTERS[i] : null}
                        index={i}
                        stale={d!.status === "closed_outdated"}
                        pos={pos}
                        frac={frac}
                        tz={tz}
                        marks={m}
                        focused={focus === `${s.id}:${c.candidate_id}`}
                        onFocus={onFocus}
                        sceneId={s.id}
                      />
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>

        <div className="sheet-lines" aria-hidden>
          <NowLine left={pos(state.production.now)} label={hhmm(state.production.now, tz)} />
          <AnimatePresence>
            {m.map((k) => (
              <motion.div key={k.label} className="mark" style={{ left: `${pos(k.at)}%` }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <motion.span
                  className="mark-line"
                  initial={{ scaleY: 0 }}
                  animate={{ scaleY: 1 }}
                  transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
                />
                <motion.span className="mark-label" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.25 }}>
                  {k.label} {hhmm(k.at, tz)}
                </motion.span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>

      <footer className="sheet-foot">
        <span>Crew call <output>{call ? hhmm(call, tz) : "--:--"}</output></span>
        <span>
          {heldCount ? <>Wrap <output>after Scene {state.scenes.filter((x) => x.validity === "held").map((x) => x.number).join(", ")} is re-planned</output></> : <>Wrap <output>{wrap ? hhmm(wrap, tz) : "--:--"}</output></>}
        </span>
      </footer>
    </section>
  );
}

function SceneRow({ scene, ghost, pos, frac, tz, marks: m, dim }: {
  scene: Scene; ghost?: ScenePlan; pos: (s: string) => number; frac: (a: string, b: string) => number;
  tz: string; marks: Mark[]; dim: boolean;
}) {
  const p = scene.plan;
  const held = scene.validity === "held";
  const hit = p && !held ? clash(m, p.people, p.end) : undefined;
  return (
    <div className="row" data-dim={dim}>
      <div className="row-label">
        <b>{String(scene.number).padStart(2, "0")}</b>
        <span className="row-title">{scene.title}</span>
        <small>{p ? (held ? "On hold" : `${title(p.location)} · ${hhmm(p.start, tz)}`) : "Not scheduled"}</small>
      </div>
      <div className="track">
        {ghost && <Ghost plan={ghost} pos={pos} frac={frac} />}
        {p && (
          <div className="block" style={{ transform: `translateX(${pos(p.start)}%)` } as CSSProperties}>
            <div
              className="face"
              data-held={held}
              data-clash={!!hit}
              style={{ "--color": sceneColor(scene.number), transform: `scaleX(${frac(p.start, p.end)})` } as CSSProperties}
            />
            <BlockText w={frac(p.start, p.end)}>
              <span className="block-loc" data-struck={held}>{title(p.location)}</span>
              <span className="block-min">{held ? "ON HOLD" : `${Math.round((+new Date(p.end) - +new Date(p.start)) / 60000)}′`}</span>
            </BlockText>
          </div>
        )}
      </div>
    </div>
  );
}

// Short blocks put their text just after the block instead of clipping it.
const NARROW = 0.11;
function BlockText({ w, children }: { w: number; children: React.ReactNode }) {
  const outside = w < NARROW;
  return (
    <div
      className="block-text"
      data-outside={outside}
      style={outside ? { left: `${w * 100}%`, width: "auto" } : { width: `${w * 100}%` }}
    >
      {children}
    </div>
  );
}

function Ghost({ plan, pos, frac }: { plan: ScenePlan; pos: (s: string) => number; frac: (a: string, b: string) => number }) {
  const w = frac(plan.start, plan.end);
  return (
    <motion.div
      className="ghost"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.25, duration: 0.3 }}
      style={{ width: `${w * 100}%`, left: `${pos(plan.start)}%` }}
    >
      <span>was {title(plan.location)}</span>
    </motion.div>
  );
}

function OptionRow({ c, letter, index, stale, pos, frac, tz, marks: m, focused, onFocus, sceneId }: {
  c: Candidate; letter: string | null; index: number; stale: boolean; pos: (s: string) => number;
  frac: (a: string, b: string) => number; tz: string; marks: Mark[]; focused: boolean;
  onFocus: (id: string | null) => void; sceneId: string;
}) {
  const mf = c.manifest;
  const out = c.check.result !== "pass";
  const hit = clash(m, mf.people, mf.end);
  const w = frac(mf.start, mf.end);
  // Where the block crosses a hard stop, the overrun is drawn in coral.
  const over = hit ? Math.max(0, Math.min(1, (pos(mf.end) - pos(hit.at)) / (pos(mf.end) - pos(mf.start)))) : 0;
  const id = `${sceneId}:${c.candidate_id}`;
  return (
    <motion.div
      className="row opt"
      data-out={out}
      data-stale={stale}
      data-focus={focused}
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.08 + index * 0.06, duration: 0.24, ease: [0.23, 1, 0.32, 1] }}
      onMouseEnter={() => onFocus(id)}
      onMouseLeave={() => onFocus(null)}
    >
      <div className="row-label opt-label">
        <i className="opt-letter" data-out={out}>{letter ?? "×"}</i>
        <span className="row-title">{c.label}</span>
        <small>{out ? c.check.reasons[0] ?? "Fails a check" : `${hhmm(mf.start, tz)}–${hhmm(mf.end, tz)}`}</small>
      </div>
      <div className="track track-opt">
        <div className="block" style={{ transform: `translateX(${pos(mf.start)}%)` }}>
          <div className="face face-opt" style={{ transform: `scaleX(${w})` }}>
            {over > 0 && <div className="overrun" style={{ width: `${over * 100}%` }} />}
          </div>
          <BlockText w={w}>
            <span className="block-loc">{title(mf.location)}</span>
          </BlockText>
        </div>
      </div>
    </motion.div>
  );
}

function NowLine({ left, label }: { left: number; label: string }) {
  if (left < 0 || left > 100) return null;
  return (
    <div className="now" style={{ left: `${left}%` }}>
      <span className="now-label">Now {label}</span>
    </div>
  );
}
