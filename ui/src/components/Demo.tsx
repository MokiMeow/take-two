// The hosted demo: a welcome card, then a strip that plays the recorded day by itself.
import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowCounterClockwise, GithubLogo, Pause, Play, YoutubeLogo } from "@phosphor-icons/react";
import { fixtures } from "../data";
import "./Demo.css";

export const FILM_URL = import.meta.env.VITE_FILM_URL || "https://github.com/MokiMeow/take-two/releases/tag/v1.0";
export const REPO_URL = "https://github.com/MokiMeow/take-two";
const RUN_URL = `${REPO_URL}/blob/main/QUICKSTART.md`;
const STEP_MS = 4200;
const EASE = [0.23, 1, 0.32, 1] as const;

// Advances one moment every few seconds while playing; stops on the last one.
export function useAutoplay(index: number, playing: boolean, setPlaying: (b: boolean) => void, setFixture: (i: number) => void) {
  useEffect(() => {
    if (!playing) return;
    if (index >= fixtures.length - 1) { setPlaying(false); return; }
    const t = window.setTimeout(() => setFixture(index + 1), STEP_MS);
    return () => window.clearTimeout(t);
  }, [index, playing, setPlaying, setFixture]);
}

export function DemoIntro({ open, onRun, onClose }: { open: boolean; onRun: () => void; onClose: () => void }) {
  const runRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    runRef.current?.focus();
    const k = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="demo-scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.25 }}>
          <motion.section
            className="demo-intro" role="dialog" aria-modal="true" aria-labelledby="demo-title"
            initial={{ opacity: 0, y: 14, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.4, ease: EASE }}
          >
            <p className="demo-eyebrow"><span className="demo-dot" /> Hosted demo</p>
            <h2 id="demo-title">A shoot day that keeps itself in sync</h2>
            <p className="demo-copy">
              When a location refuses, an actor runs late or a recorder dies, Take Two holds the scenes, asks two agents for plans,
              checks them in code and lets the director pick on a Switch card. The new call sheet goes to Mattermost and Discord.
            </p>
            <p className="demo-copy demo-small">
              This page replays a day recorded against a real Switch server: 26 moments, 5 releases. Nothing here is live and nothing is sent.
            </p>
            <div className="demo-actions">
              <button ref={runRef} className="btn btn-primary demo-run" onClick={onRun}><Play size={15} weight="fill" /> Run the demo</button>
              <a className="btn" href={FILM_URL} target="_blank" rel="noreferrer"><YoutubeLogo size={16} /> Watch the film</a>
              <a className="btn" href={RUN_URL} target="_blank" rel="noreferrer"><GithubLogo size={16} /> Run it yourself</a>
            </div>
            <button className="demo-skip" onClick={onClose}>Explore on my own</button>
          </motion.section>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function DemoBar({ index, playing, onToggle }: { index: number; playing: boolean; onToggle: () => void }) {
  const last = index >= fixtures.length - 1;
  return (
    <div className="demo-bar" role="region" aria-label="Demo">
      <span className="demo-tag"><span className="demo-dot" /> Demo · replay of the recorded day</span>
      <button className="demo-play" onClick={onToggle} aria-label={playing ? "Pause the demo" : last ? "Play the demo again" : "Play the demo"}>
        {playing ? <Pause size={13} weight="fill" /> : last ? <ArrowCounterClockwise size={13} weight="bold" /> : <Play size={13} weight="fill" />}
        <span>{playing ? "Pause" : last ? "Play again" : "Play"}</span>
      </button>
      <span className="demo-track" aria-hidden>
        <motion.span className="demo-fill" initial={false} animate={{ scaleX: (index + 1) / fixtures.length }} transition={{ duration: 0.5, ease: EASE }} />
      </span>
      <span className="demo-count">{index + 1}/{fixtures.length}</span>
      <span className="demo-links">
        <a href={FILM_URL} target="_blank" rel="noreferrer"><YoutubeLogo size={14} /> <span>Watch the film</span></a>
        <a href={REPO_URL} target="_blank" rel="noreferrer"><GithubLogo size={14} /> <span>Source</span></a>
      </span>
    </div>
  );
}
